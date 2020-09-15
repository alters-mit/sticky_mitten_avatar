import random
import numpy as np
from pkg_resources import resource_filename
from typing import Dict, List, Union, Optional, Tuple
from tdw.controller import Controller
from tdw.tdw_utils import TDWUtils
from tdw.librarian import ModelLibrarian
from tdw.output_data import Bounds, Transforms, Rigidbodies, SegmentationColors, Volumes, Raycast
from tdw.py_impact import AudioMaterial, PyImpact, ObjectInfo
from sticky_mitten_avatar.avatars import Arm, Baby
from sticky_mitten_avatar.avatars.avatar import Avatar, Joint, BodyPartStatic
from sticky_mitten_avatar.util import get_data, get_angle, rotate_point_around, get_angle_between, FORWARD
from sticky_mitten_avatar.static_object_info import StaticObjectInfo
from sticky_mitten_avatar.frame_data import FrameData
from sticky_mitten_avatar.task_status import TaskStatus


class StickyMittenAvatarController(Controller):
    """
    High-level API controller for sticky mitten avatars.

    ```python
    from sticky_mitten_avatar import StickyMittenAvatarController, Arm

    c = StickyMittenAvatarController()

    # Load a simple scene and create the avatar.
    c.init_scene()

    # Bend an arm.
    task_status = c.reach_for_target(target={"x": -0.2, "y": 0.21, "z": 0.385}, arm=Arm.left)
    print(task_status) # TaskStatus.success

    # Get the segmentation color pass for the avatar after bending the arm.
    # See FrameData.save_images and FrameData.get_pil_images
    segmentation_colors = c.frames[-1].id_pass

    c.end()
    ```

    All parameters of type `Dict[str, float]` are Vector3 dictionaries formatted like this:

    ```json
    {"x": -0.2, "y": 0.21, "z": 0.385}
    ```

    `y` is the up direction.

    To convert from or to a numpy array:

    ```python
    from tdw.tdw_utils import TDWUtils

    target = {"x": 1, "y": 0, "z": 0}
    target = TDWUtils.vector3_to_array(target)
    print(target) # [1 0 0]
    target = TDWUtils.array_to_vector3(target)
    print(target) # {'x': 1.0, 'y': 0.0, 'z': 0.0}
    ```

    A parameter of type `Union[Dict[str, float], int]]` can be either a Vector3 or an integer (an object ID).

    ***

    ## Fields

    - `frames` Dynamic data for all of the frames from the previous avatar API call (e.g. `reach_for_target()`). [Read this](frame_data.md) for a full API.
      The next time an API call is made, this list is cleared and filled with new data.

    ```python
    # Get the segmentation colors and depth map from the most recent frame.
    id_pass = c.frames[-1].id_pass
    depth_pass = c.frames[-1].depth_pass
    # etc.
    ```

    - `static_object_data`: Static info for all objects in the scene. [Read this](static_object_info.md) for a full API.

    ```python
    # Get the segmentation color of an object.
    segmentation_color = c.static_object_info[object_id].segmentation_color
    ```

    - `static_avatar_data` Static info for the avatar's body parts. [Read this](body_part_static.md) for a full API.

    ```python
    for body_part_id in c.static_avatar_data.avatar:
        body_part = c.static_avatar_data.avatars[body_part_id]
        print(body_part.object_id) # The object ID of the body part (matches body_part_id).
        print(body_part.color) # The segmentation color.
        print(body_part.name) # The name of the body part.
    ```

    ## Functions

    """

    # A high drag value to stop movement.
    _STOP_DRAG = 1000

    _STATIC_FRICTION = {AudioMaterial.ceramic: 0.47,
                        AudioMaterial.hardwood: 0.4,
                        AudioMaterial.wood: 0.4,
                        AudioMaterial.cardboard: 0.47,
                        AudioMaterial.glass: 0.65,
                        AudioMaterial.metal: 0.52}
    _DYNAMIC_FRICTION = {AudioMaterial.ceramic: 0.47,
                         AudioMaterial.hardwood: 0.35,
                         AudioMaterial.wood: 0.35,
                         AudioMaterial.cardboard: 0.47,
                         AudioMaterial.glass: 0.65,
                         AudioMaterial.metal: 0.43}

    def __init__(self, port: int = 1071, launch_build: bool = True, audio_playback_mode: str = None):
        """
        :param port: The port number.
        :param launch_build: If True, automatically launch the build.
        :param audio_playback_mode: How the build will play back audio. Options: None (no playback, but audio will be generated in `self.frame_data`), `"unity"` (use the standard Unity audio system), `"resonance_audio"` (use Resonance Audio).
        """

        # The containers library.
        self._lib_containers = ModelLibrarian(library=resource_filename(__name__, "metadata_libraries/containers.json"))
        # Cached core model library.
        self._lib_core = ModelLibrarian()

        # Cache the entities.
        self._avatar: Optional[Avatar] = None
        # Commands sent by avatars.
        self._avatar_commands: List[dict] = []
        # Cache static data.
        self.static_object_info: Dict[int, StaticObjectInfo] = dict()
        self.static_avatar_info: Dict[int, BodyPartStatic] = dict()
        self._audio_playback_mode = audio_playback_mode
        # Load default audio values for objects.
        self._default_audio_values = PyImpact.get_object_info()
        # Load custom audio values.
        custom_audio_info = PyImpact.get_object_info(resource_filename(__name__, "audio.csv"))
        for a in custom_audio_info:
            av = custom_audio_info[a]
            av.library = resource_filename(__name__, av.library)
            self._default_audio_values[a] = av

        self._audio_values: Dict[int, ObjectInfo] = dict()

        # The command for the third-person camera, if any.
        self._cam_commands: Optional[list] = None

        self.frames: List[FrameData] = list()

        super().__init__(port=port, launch_build=launch_build)

        # Set image encoding to .jpg
        # Set the highest render quality.
        # Set global physics values.
        commands = [{"$type": "set_img_pass_encoding",
                     "value": False},
                    {"$type": "set_render_quality",
                     "render_quality": 5},
                    {"$type": "set_physics_solver_iterations",
                     "iterations": 32},
                    {"$type": "set_vignette",
                     "enabled": False},
                    {"$type": "set_shadow_strength",
                     "strength": 1.0},
                    {"$type": "set_sleep_threshold",
                     "sleep_threshold": 0.1}]
        # Set the frame rate and timestep for audio.
        if self._audio_playback_mode is not None:
            commands.extend([{"$type": "set_target_framerate",
                             "framerate": 30},
                             {"$type": "set_time_step",
                              "time_step": 0.02}])

    def init_scene(self) -> None:
        """
        Initialize a scene, populate it with objects, add the avatar, and set rendering options.
        Then, request data per frame (collisions, transforms, etc.), initialize image capture, and cache static data.

        Each subclass of `StickyMittenAvatarController` overrides this function to have a specialized scene setup.
        """

        self._start_task()

        # Initialize the scene.
        self.communicate(self._get_scene_init_commands_early())
        # Create the avatar.
        self._init_avatar()
        # Initialize after adding avatars.
        self._do_scene_init_late()

        # Request Collisions, Rigidbodies, and Transforms.
        # Request SegmentationColors, Bounds, and Volumes for this frame only.
        resp = self.communicate([{"$type": "send_collisions",
                                  "enter": True,
                                  "stay": False,
                                  "exit": False,
                                  "collision_types": ["obj", "env"]},
                                 {"$type": "send_rigidbodies",
                                  "frequency": "always"},
                                 {"$type": "send_transforms",
                                  "frequency": "always"},
                                 {"$type": "send_segmentation_colors",
                                  "frequency": "once"},
                                 {"$type": "send_bounds",
                                  "frequency": "once"},
                                 {"$type": "send_volumes",
                                  "frequency": "once"}])

        # Cache the static object data.
        segmentation_colors = get_data(resp=resp, d_type=SegmentationColors)
        bounds = get_data(resp=resp, d_type=Bounds)
        volumes = get_data(resp=resp, d_type=Volumes)
        rigidbodies = get_data(resp=resp, d_type=Rigidbodies)
        for i in range(segmentation_colors.get_num()):
            object_id = segmentation_colors.get_object_id(i)
            static_object = StaticObjectInfo(index=i,
                                             segmentation_colors=segmentation_colors,
                                             rigidbodies=rigidbodies,
                                             volumes=volumes,
                                             bounds=bounds,
                                             audio=self._audio_values[object_id])
            self.static_object_info[static_object.object_id] = static_object

    def _create_avatar(self, avatar_type: str = "baby", avatar_id: str = "a", position: Dict[str, float] = None,
                       rotation: float = 0, debug: bool = False) -> None:
        """
        Create an avatar. Set default values for the avatar. Cache its static data (segmentation colors, etc.)

        :param avatar_type: The type of avatar. Options: "baby", "adult"
        :param avatar_id: The unique ID of the avatar.
        :param position: The initial position of the avatar.
        :param rotation: The initial rotation of the avatar in degrees.
        :param debug: If true, print debug messages when the avatar moves.
        """

        if avatar_type == "baby":
            avatar_type = "A_StickyMitten_Baby"
        elif avatar_type == "adult":
            avatar_type = "A_StickyMitten_Adult"
        else:
            raise Exception(f'Avatar type not found: {avatar_type}\nOptions: "baby", "adult"')

        if position is None:
            position = {"x": 0, "y": 0, "z": 0}

        commands = TDWUtils.create_avatar(avatar_type=avatar_type,
                                          avatar_id=avatar_id,
                                          position=position)[:]
        # Rotate the avatar.
        # Request segmentation colors, body part names, and dynamic avatar data.
        # Turn off the follow camera.
        # Set the palms to sticky.
        # Enable image capture.
        commands.extend([{"$type": "rotate_avatar_by",
                          "angle": rotation,
                          "axis": "yaw",
                          "is_world": True,
                          "avatar_id": avatar_id},
                         {"$type": "send_avatar_segmentation_colors",
                          "frequency": "once",
                          "ids": [avatar_id]},
                         {"$type": "send_avatars",
                          "frequency": "always"},
                         {"$type": "set_avatar_collision_detection_mode",
                          "mode": "continuous_dynamic",
                          "avatar_id": avatar_id},
                         {"$type": "set_avatar_drag",
                          "drag": self._STOP_DRAG,
                          "angular_drag": self._STOP_DRAG,
                          "avatar_id": avatar_id},
                         {"$type": "set_pass_masks",
                          "pass_masks": ["_img", "_id", "_depth_simple"],
                          "avatar_id": avatar_id},
                         {"$type": "send_images",
                          "frequency": "always"},
                         {"$type": "toggle_image_sensor",
                          "sensor_name": "FollowCamera",
                          "avatar_id": avatar_id}])
        # Set all sides of both mittens to be sticky.
        for sub_mitten in ["palm", "back", "side"]:
            for is_left in [True, False]:
                commands.append({"$type": "set_stickiness",
                                 "sub_mitten": sub_mitten,
                                 "sticky": True,
                                 "is_left": is_left,
                                 "avatar_id": avatar_id,
                                 "show": False})
        # Strengthen the avatar.
        for joint in Avatar.JOINTS:
            commands.extend([{"$type": "adjust_joint_force_by",
                              "delta": 80,
                              "joint": joint.joint,
                              "axis": joint.axis,
                              "avatar_id": avatar_id},
                             {"$type": "adjust_joint_damper_by",
                              "delta": 300,
                              "joint": joint.joint,
                              "axis": joint.axis,
                              "avatar_id": avatar_id}])

        if self._audio_playback_mode == "unity":
            commands.append({"$type": "add_audio_sensor",
                             "avatar_id": avatar_id})
        elif self._audio_playback_mode == "resonance_audio":
            commands.append({"$type": "add_environ_audio_sensor",
                             "avatar_id": avatar_id})

        # Send the commands. Get a response.
        resp = self.communicate(commands)
        # Create the avatar.
        if avatar_type == "A_StickyMitten_Baby":
            avatar = Baby(avatar_id=avatar_id, debug=debug, resp=resp)
        else:
            raise Exception(f"Avatar not defined: {avatar_type}")
        # Cache the avatar.
        self._avatar = avatar
        self.static_avatar_info = self._avatar.body_parts_static

    def communicate(self, commands: Union[dict, List[dict]]) -> List[bytes]:
        """
        Overrides [`Controller.communicate()`](https://github.com/threedworld-mit/tdw/blob/master/Documentation/python/controller.md).
        Before sending commands, append any automatically-added commands (such as arm-bending or arm-stopping).
        If there is a third-person camera, append commands to look at a target (see `add_overhead_camera()`).
        After receiving a response from the build, update the `frame` data.

        :param commands: Commands to send to the build.

        :return: The response from the build.
        """
        if not isinstance(commands, list):
            commands = [commands]
        # Add avatar commands from the previous frame.
        commands.extend(self._avatar_commands[:])

        # Append the third-party look-at command, if any.
        if self._cam_commands is not None:
            commands.extend(self._cam_commands)

        # Clear avatar commands.
        self._avatar_commands.clear()

        # Add audio commands.
        commands.extend(self._get_audio_commands())

        # Send the commands and get a response.
        resp = super().communicate(commands)

        if len(resp) == 1:
            return resp

        # Update object info.
        tran = get_data(resp=resp, d_type=Transforms)
        rigi = get_data(resp=resp, d_type=Rigidbodies)

        if tran is None or rigi is None:
            return resp

        # Update the frame data.
        self.frames.append(FrameData(resp=resp, objects=self.static_object_info, avatar=self._avatar))

        # Update the avatar. Add new avatar commands for the next frame.
        if self._avatar is not None:
            self._avatar_commands.extend(self._avatar.on_frame(resp=resp))

        return resp

    def _add_object(self, model_name: str, object_id: int, position: Dict[str, float] = None,
                    rotation: Dict[str, float] = None, library: str = "",
                    scale: Dict[str, float] = None, audio: ObjectInfo = None) -> List[dict]:
        """
        Add an object to the scene.

        :param model_name: The name of the model.
        :param position: The position of the model.
        :param rotation: The starting rotation of the model, in Euler angles.
        :param library: The path to the records file. If left empty, the default library will be selected.
                        See `ModelLibrarian.get_library_filenames()` and `ModelLibrarian.get_default_library()`.
        :param object_id: The ID of the new object.
        :param scale: The scale factor of the object. If None, the scale factor is (1, 1, 1)
        :param audio: Audio values for the object. If None, use default values.

        :return: A list of commands: `[add_object, set_mass, scale_object ,set_object_collision_detection_mode, set_physic_material]`
        """

        if position is None:
            position = {"x": 0, "y": 0, "z": 0}
        if rotation is None:
            rotation = {"x": 0, "y": 0, "z": 0}
        if scale is None:
            scale = {"x": 1, "y": 1, "z": 1}
        if audio is None:
            audio = self._default_audio_values[model_name]
        self._audio_values[object_id] = audio

        return [super().get_add_object(model_name=model_name, object_id=object_id, position=position,
                                       rotation=rotation, library=library),
                {"$type": "set_mass",
                 "mass": audio.mass,
                 "id": object_id},
                {"$type": "scale_object",
                 "id": object_id,
                 "scale_factor": scale},
                {"$type": "set_object_collision_detection_mode",
                 "id": object_id,
                 "mode": "continuous_dynamic"},
                {"$type": "set_physic_material",
                 "dynamic_friction": StickyMittenAvatarController._DYNAMIC_FRICTION[audio.material],
                 "static_friction": StickyMittenAvatarController._STATIC_FRICTION[audio.material],
                 "bounciness": audio.bounciness,
                 "id": object_id}]

    def _add_container(self, model_name: str, object_id: int, contents: List[str], position: Dict[str, float] = None,
                       rotation: Dict[str, float] = None, audio: ObjectInfo = None,
                       scale: Dict[str, float] = None) -> List[dict]:
        """
        Add a container to the scene. A container is an object that can hold other objects in it.
        Containers must be from the "containers" library. See `get_container_records()`.

        :param model_name: The name of the container.
        :param object_id: The ID of the container.
        :param contents: The model names of objects that will be put in the container. They will be assigned random positions and object IDs and default audio and physics values.
        :param position: The position of the container.
        :param rotation: The rotation of the container.
        :param audio: Audio values for the container. If None, use default values.
        :param scale: The scale of the container.

        :return: A list of commands per object added: `[add_object, set_mass, scale_object ,set_object_collision_detection_mode, set_physic_material]`
        """

        record = self._lib_containers.get_record(model_name)
        assert record is not None, f"Couldn't find container record for: {model_name}"

        if position is None:
            position = {"x": 0, "y": 0, "z": 0}

        # Get commands to add the container.
        commands = self._add_object(model_name=model_name, object_id=object_id, position=position, rotation=rotation,
                                    library=self._lib_containers.library, audio=audio, scale=scale)
        bounds = record.bounds
        # Get the radius in which objects can reasonably be placed.
        radius = (min(bounds['front']['z'] - bounds['back']['z'],
                      bounds['right']['x'] - bounds['left']['x']) / 2 * record.scale_factor) - 0.03
        # Add small objects.
        for obj_name in contents:
            obj = self._default_audio_values[obj_name]
            o_pos = TDWUtils.array_to_vector3(TDWUtils.get_random_point_in_circle(
                center=TDWUtils.vector3_to_array(position),
                radius=radius))
            o_pos["y"] = position["y"] + 0.01
            commands.extend(self._add_object(model_name=obj.name, position=o_pos, audio=obj,
                                             object_id=self.get_unique_id(), library=obj.library))
        self.model_librarian = self._lib_core
        return commands

    def reach_for_target(self, arm: Arm, target: Dict[str, float], do_motion: bool = True,
                         check_if_possible: bool = True) -> TaskStatus:
        """
        Bend an arm joints of an avatar to reach for a target position.

        Possible [return values](task_status.md):

        - `success` (The avatar's arm's mitten reached the target position.)
        - `too_close_to_reach`
        - `too_far_to_reach`
        - `behind_avatar`
        - `no_longer_bending`

        :param arm: The arm (left or right).
        :param target: The target position for the mitten relative to the avatar.
        :param do_motion: If True, advance simulation frames until the pick-up motion is done.
        :param check_if_possible: If True, before bending the arm, check if the mitten can reach the target assuming no obstructions; if not, don't try to bend the arm.

        :return: A `TaskStatus` indicating whether the avatar can reach the target and if not, why.
        """

        self._start_task()

        target = TDWUtils.vector3_to_array(target)

        # Check if it is possible for the avatar to reach the target.
        if check_if_possible:
            status = self._avatar.can_reach_target(target=target, arm=arm)
            if status != TaskStatus.success:
                return status

        self._avatar_commands.extend(self._avatar.reach_for_target(arm=arm, target=target))
        self._avatar.status = TaskStatus.ongoing
        if do_motion:
            self._do_joint_motion()
        return self._get_avatar_status()

    def grasp_object(self, object_id: int, arm: Arm, do_motion: bool = True, check_if_possible: bool = True) -> TaskStatus:
        """
        The avatar's arm will reach for the object. Per frame, the arm's mitten will try to "grasp" the object.
        A grasped object is attached to the avatar's mitten and its ID will be in [`FrameData.held_objects`](frame_data.md). There may be some empty space between a mitten and a grasped object.
        This task ends when the avatar grasps the object (at which point it will stop bending its arm), or if it fails to grasp the object (see below).

        Possible [return values](task_status.md):

        - `success` (The avatar picked up the object.)
        - `too_close_to_reach`
        - `too_far_to_reach`
        - `behind_avatar`
        - `no_longer_bending`
        - `failed_to_pick_up`
        - `bad_raycast`

        :param object_id: The ID of the target object.
        :param do_motion: If True, advance simulation frames until the pick-up motion is done.
        :param arm: The arm of the mitten that will try to grasp the object.
        :param check_if_possible: If True, before bending the arm, check if the mitten can reach the target assuming no obstructions; if not, don't try to bend the arm.

        :return: A `TaskStatus` indicating whether the avatar picked up the object and if not, why.
        """

        self._start_task()

        # Get the mitten's position.
        if arm == Arm.left:
            mitten = np.array(self._avatar.frame.get_mitten_center_left_position())
        else:
            mitten = np.array(self._avatar.frame.get_mitten_center_right_position())
        # Raycast to the target to get a target position.
        raycast_ok, target = self._get_raycast_point(origin=mitten, object_id=object_id, forward=0.01)

        if check_if_possible:
            if not raycast_ok:
                return TaskStatus.bad_raycast
            reachable_target = self._avatar.get_rotated_target(target=target)
            status = self._avatar.can_reach_target(target=reachable_target, arm=arm)
            if status != TaskStatus.success:
                return status

        # Get commands to pick up the target.
        commands = self._avatar.grasp_object(object_id=object_id, target=target, arm=arm)

        self._avatar_commands.extend(commands)
        self._avatar.status = TaskStatus.ongoing
        if do_motion:
            self._do_joint_motion()
        # The avatar failed to reach the target.
        if self._avatar.status != TaskStatus.success:
            return self._get_avatar_status()

        # Return whether the avatar picked up the object.
        self._avatar.status = TaskStatus.idle
        if self._avatar.is_holding(object_id=object_id):
            return TaskStatus.success
        else:
            return TaskStatus.failed_to_pick_up

    def drop(self, reset_arms: bool = True, do_motion: bool = True) -> TaskStatus:
        """
        Drop any held objects and reset the arms to their neutral positions.

        :param reset_arms: If True, reset arm positions to "neutral".
        :param do_motion: If True, advance simulation frames until the pick-up motion is done.
        """

        self._start_task()

        self._avatar_commands.extend(self._avatar.drop(reset_arms=reset_arms))
        if do_motion:
            self._do_joint_motion()
        return TaskStatus.success

    def reset_arms(self, do_motion: bool = True) -> TaskStatus:
        """
        Reset the avatar's arms to their neutral positions.

        :param do_motion: If True, advance simulation frames until the pick-up motion is done.
        """

        self._start_task()

        self._avatar_commands.extend(self._avatar.reset_arms())
        if do_motion:
            self._do_joint_motion()
        return TaskStatus.success

    def _do_joint_motion(self) -> None:
        """
        Step through the simulation until the joints of all avatars are done moving.
        Useful when you want concurrent action.
        """

        done = False
        while not done:
            done = True
            # The loop is done if the IK goals are done.
            if not self._avatar.is_ik_done():
                done = False
            # Keep looping.
            if not done:
                self.communicate([])

    def _stop_avatar(self) -> None:
        """
        Advance 1 frame and stop the avatar's movement and turning.
        """

        self.communicate({"$type": "set_avatar_drag",
                          "drag": self._STOP_DRAG,
                          "angular_drag": self._STOP_DRAG,
                          "avatar_id": self._avatar.id})
        self._avatar.status = TaskStatus.idle

    def turn_to(self, target: Union[Dict[str, float], int], force: float = 1000,
                stopping_threshold: float = 0.15) -> TaskStatus:
        """
        Turn the avatar to face a target position or object.

        Possible [return values](task_status.md):

        - `success` (The avatar turned to face the target.)
        - `turned_360`
        - `too_long`

        :param target: Either the target position or the ID of the target object.
        :param force: The force at which the avatar will turn. More force = faster, but might overshoot the target.
        :param stopping_threshold: Stop when the avatar is within this many degrees of the target.

        :return: A `TaskStatus` indicating whether the avatar turned successfully and if not, why.
        """

        def _get_turn_state() -> Tuple[TaskStatus, float]:
            """
            :return: Whether avatar succeed, failed, or is presently turning and the current angle.
            """

            angle = get_angle(origin=np.array(self._avatar.frame.get_position()),
                              forward=np.array(self._avatar.frame.get_forward()),
                              position=target)
            # Arrived at the right again.
            if np.abs(angle) < stopping_threshold:
                print("ARRIVAL")
                return TaskStatus.success, angle

            return TaskStatus.ongoing, angle

        self._start_task()

        # Set the target if it wasn't already a numpy array (for example, if it's an object ID).
        target = self._get_position(target=target)
        target[1] = 0
        # Get the angle to the target.
        initial_angle = get_angle(origin=np.array(self._avatar.frame.get_position()),
                                  forward=np.array(self._avatar.frame.get_forward()),
                                  position=target)
        if initial_angle < 0:
            direction = -1
        else:
            direction = 1

        self._avatar.status = TaskStatus.ongoing

        # Set a low drag.
        self.communicate({"$type": "set_avatar_drag",
                          "drag": 0,
                          "angular_drag": 0.05,
                          "avatar_id": self._avatar.id})

        turn_command = {"$type": "turn_avatar_by",
                        "torque": force * direction,
                        "avatar_id": self._avatar.id}

        # Begin to turn.
        self.communicate(turn_command)
        i = 0
        while i < 200:
            # Coast to a stop.
            coasting = True
            while coasting:
                coasting = np.linalg.norm(self._avatar.frame.get_angular_velocity()) > 0.3
                state, previous_angle = _get_turn_state()
                # The turn succeeded!
                if state == TaskStatus.success:
                    self._stop_avatar()
                    return state
                # The turn failed.
                elif state != TaskStatus.ongoing:
                    self._stop_avatar()
                    return state
                self.communicate([])

            # Turn.
            self.communicate(turn_command)
            state, previous_angle = _get_turn_state()
            # The turn succeeded!
            if state == TaskStatus.success:
                self._stop_avatar()
                return state
            # The turn failed.
            elif state != TaskStatus.ongoing:
                self._stop_avatar()
                return state
            i += 1
        self._stop_avatar()
        return TaskStatus.too_long

    def turn_by(self, angle: float, force: float = 1000, stopping_threshold: float = 0.15) -> TaskStatus:
        """
        Turn the avatar by an angle.

        Possible [return values](task_status.md):

        - `success` (The avatar turned by the angle.)
        - `too_long`

        :param angle: The angle to turn to in degrees. If > 0, turn clockwise; if < 0, turn counterclockwise.
        :param force: The force at which the avatar will turn. More force = faster, but might overshoot the target.
        :param stopping_threshold: Stop when the avatar is within this many degrees of the target.

        :return: A `TaskStatus` indicating whether the avatar turned successfully and if not, why.
        """

        # Rotate the forward directional vector.
        p0 = self._avatar.frame.get_forward()
        p1 = rotate_point_around(origin=np.array([0, 0, 0]), point=p0, angle=angle)
        # Get a point to look at.
        p1 = np.array(self._avatar.frame.get_position()) + (p1 * 1000)
        return self.turn_to(target=TDWUtils.array_to_vector3(p1), force=force, stopping_threshold=stopping_threshold)

    def go_to(self, target: Union[Dict[str, float], int], turn_force: float = 1000, move_force: float = 80,
              turn_stopping_threshold: float = 0.15, move_stopping_threshold: float = 0.35) -> TaskStatus:
        """
        Move the avatar to a target position or object.

        Possible [return values](task_status.md):

        - `success` (The avatar arrived at the target.)
        - `too_long`
        - `overshot`
        - `collided_with_something_heavy`
        - `collided_with_environment`

        :param target: Either the target position or the ID of the target object.
        :param turn_force: The force at which the avatar will turn. More force = faster, but might overshoot the target.
        :param turn_stopping_threshold: Stop when the avatar is within this many degrees of the target.
        :param move_force: The force at which the avatar will move. More force = faster, but might overshoot the target.
        :param move_stopping_threshold: Stop within this distance of the target.

        :return:  A `TaskStatus` indicating whether the avatar arrived at the target and if not, why.
        """

        def _get_state() -> TaskStatus:
            """
            :return: Whether the avatar is at its destination, overshot it, or still going to it.
            """

            # Check if the root object of the avatar collided with anything large. If so, stop movement.
            for body_part_id in self._avatar.collisions:
                name = self._avatar.body_parts_static[body_part_id].name
                if name.startswith("A_StickyMitten"):
                    for o_id in self._avatar.collisions[body_part_id]:
                        collidee_mass = self.static_object_info[o_id].mass
                        if collidee_mass >= 90:
                            return TaskStatus.collided_with_something_heavy
            # If the avatar's body collided with the environment (e.g. a wall), stop movement.
            for body_part_id in self._avatar.env_collisions:
                name = self._avatar.body_parts_static[body_part_id].name
                if name.startswith("A_StickyMitten"):
                    return TaskStatus.collided_with_environment

            p = np.array(self._avatar.frame.get_position())
            d_from_initial = np.linalg.norm(initial_position - p)
            # Overshot. End.
            if d_from_initial > initial_distance:
                return TaskStatus.overshot
            # We're here! End.
            d = np.linalg.norm(p - target)
            if d <= move_stopping_threshold:
                return TaskStatus.success
            # Keep truckin' along.
            return TaskStatus.ongoing

        self._start_task()

        initial_position = self._avatar.frame.get_position()

        # Set the target. If it's an object, the target is the nearest point on the bounds.
        target = self._get_position(target=target)
        # Get the distance to the target.
        initial_distance = np.linalg.norm(np.array(initial_position) - target)

        # Turn to the target.
        status = self.turn_to(target=target, force=turn_force, stopping_threshold=turn_stopping_threshold)
        if status != TaskStatus.success:
            return status

        self._avatar.status = TaskStatus.ongoing

        # Go to the target.
        self.communicate({"$type": "set_avatar_drag",
                          "drag": 0.1,
                          "angular_drag": 100,
                          "avatar_id": self._avatar.id})
        i = 0
        while i < 200:
            # Start gliding.
            self.communicate({"$type": "move_avatar_forward_by",
                              "magnitude": move_force,
                              "avatar_id": self._avatar.id})
            t = _get_state()
            if t == TaskStatus.success:
                self._stop_avatar()
                return t
            elif t != TaskStatus.ongoing:
                self._stop_avatar()
                return t
            # Glide.
            while np.linalg.norm(self._avatar.frame.get_velocity()) > 0.1:
                self.communicate([])
                t = _get_state()
                if t == TaskStatus.success:
                    self._stop_avatar()
                    return t
                elif t != TaskStatus.ongoing:
                    self._stop_avatar()
                    return t
            i += 1
        self._stop_avatar()
        return TaskStatus.too_long

    def move_forward_by(self, distance: float, move_force: float = 80, move_stopping_threshold: float = 0.35) -> \
            TaskStatus:
        """
        Move the avatar forward by a distance along the avatar's current forward directional vector.

        Possible [return values](task_status.md):

        - `success` (The avatar moved forward by the distance.)
        - `turned_360`
        - `too_long`
        - `overshot`
        - `collided_with_something_heavy`
        - `collided_with_environment`

        :param distance: The distance that the avatar will travel. If < 0, the avatar will move backwards.
        :param move_force: The force at which the avatar will move. More force = faster, but might overshoot the target.
        :param move_stopping_threshold: Stop within this distance of the target.

        :return: A `TaskStatus` indicating whether the avatar moved forward by the distance and if not, why.
        """

        # The target is at `distance` away from the avatar's position along the avatar's forward directional vector.
        target = np.array(self._avatar.frame.get_position()) + (np.array(self._avatar.frame.get_forward()) * distance)
        return self.go_to(target=target, move_force=move_force, move_stopping_threshold=move_stopping_threshold)

    def shake(self, joint_name: str = "elbow_left", axis: str = "pitch", angle: Tuple[float, float] = (20, 30),
              num_shakes: Tuple[int, int] = (3, 5), force: Tuple[float, float] = (900, 1000)) -> None:
        """
        Shake an avatar's arm for multiple iterations.
        Per iteration, the joint will bend forward by an angle and then bend back by an angle.
        The motion ends when all of the avatar's joints have stopped moving.

        :param joint_name: The name of the joint.
        :param axis: The axis of the joint's rotation.
        :param angle: Each shake will bend the joint by a angle in degrees within this range.
        :param num_shakes: The avatar will shake the joint a number of times within this range.
        :param force: The avatar will add strength to the joint by a value within this range.
        """

        self._start_task()

        # Check if the joint and axis are valid.
        joint: Optional[Joint] = None
        for j in Avatar.JOINTS:
            if j.joint == joint_name and j.axis == axis:
                joint = j
                break
        if joint is None:
            return

        force = random.uniform(force[0], force[1])
        damper = 200
        # Increase the force of the joint.
        self.communicate([{"$type": "adjust_joint_force_by",
                           "delta": force,
                           "joint": joint.joint,
                           "axis": joint.axis,
                           "avatar_id": self._avatar.id},
                          {"$type": "adjust_joint_damper_by",
                           "delta": -damper,
                           "joint": joint.joint,
                           "axis": joint.axis,
                           "avatar_id": self._avatar.id}])
        # Do each iteration.
        for i in range(random.randint(num_shakes[0], num_shakes[1])):
            a = random.uniform(angle[0], angle[1])
            # Start the shake.
            self.communicate({"$type": "bend_arm_joint_by",
                              "angle": a,
                              "joint": joint.joint,
                              "axis": joint.axis,
                              "avatar_id": self._avatar.id})
            for j in range(10):
                self.communicate([])
            # Bend the arm back.
            self.communicate({"$type": "bend_arm_joint_by",
                              "angle": -(a / 2),
                              "joint": joint.joint,
                              "axis": joint.axis,
                              "avatar_id": self._avatar.id})
            for j in range(50):
                self.communicate([])
            # Apply the motion.
            self._do_joint_motion()
        # Reset the force of the joint.
        self.communicate([{"$type": "adjust_joint_force_by",
                           "delta": -force,
                           "joint": joint.joint,
                           "axis": joint.axis,
                           "avatar_id": self._avatar.id},
                          {"$type": "adjust_joint_damper_by",
                           "delta": damper,
                           "joint": joint.joint,
                           "axis": joint.axis,
                           "avatar_id": self._avatar.id}])

    def rotate_camera_by(self, pitch: float = 0, yaw: float = 0, roll: float = 0) -> None:
        """
        Rotate an avatar's camera around each axis.
        The head of the avatar won't visually rotate (as this could put the avatar off-balance).
        Advances the simulation by 1 frame.

        :param pitch: Pitch (nod your head "yes") the camera by this angle, in degrees.
        :param yaw: Yaw (shake your head "no") the camera by this angle, in degrees.
        :param roll: Roll (put your ear to your shoulder) the camera by this angle, in degrees.
        """

        self._start_task()

        commands = []
        for angle, axis in zip([pitch, yaw, roll], ["pitch", "yaw", "roll"]):
            commands.append({"$type": "rotate_sensor_container_by",
                             "axis": axis,
                             "angle": angle,
                             "avatar_id": self._avatar.id})
        self.communicate(commands)

    def reset_camera_rotation(self) -> None:
        """
        Reset the rotation of the avatar's camera.
        Advances the simulation by 1 frame.
        """

        self._start_task()

        self.communicate({"$type": "reset_sensor_container_rotation",
                          "avatar_id": self._avatar.id})

    def add_overhead_camera(self, position: Dict[str, float], target_object: Union[str, int] = None, cam_id: str = "c",
                            images: str = "all") -> None:
        """
        Add an overhead third-person camera to the scene.

        :param cam_id: The ID of the camera.
        :param target_object: Always point the camera at this object or avatar.
        :param position: The position of the camera.
        :param images: Image capture behavior. Choices:
                       1. `"cam"` (only this camera captures images)
                       2. `"all"` (avatars currently in the scene and this camera capture images)
                       3. `"avatars"` (only the avatars currently in the scene capture images)
        """

        self._start_task()

        commands = TDWUtils.create_avatar(avatar_type="A_Img_Caps_Kinematic",
                                          avatar_id=cam_id,
                                          position=position)
        if target_object is not None:
            # Get the avatar's object ID.
            if isinstance(target_object, str):
                self._cam_commands = [{"$type": "look_at_avatar",
                                       "target_avatar_id": target_object,
                                       "avatar_id": cam_id,
                                       "use_centroid": True},
                                      {"$type": "rotate_sensor_container_by",
                                       "axis": "pitch",
                                       "angle": -5,
                                       "avatar_id": cam_id}]
            else:
                self._cam_commands = [{"$type": "look_at",
                                       "object_id": target_object,
                                       "avatar_id": cam_id,
                                       "use_centroid": True}]
        if images != "avatars":
            commands.append({"$type": "set_pass_masks",
                             "pass_masks": ["_img"],
                             "avatar_id": cam_id})
        if images == "cam":
            # Disable avatar cameras.
            commands.append({"$type": "toggle_image_sensor",
                             "sensor_name": "SensorContainer"})

            commands.append({"$type": "send_images",
                             "ids": [cam_id],
                             "frequency": "always"})
        elif images == "all":
            commands.append({"$type": "send_images",
                             "frequency": "always"})
        self.communicate(commands)

    def _destroy_avatar(self, avatar_id: str) -> None:
        """
        Destroy an avatar or camera in the scene.

        :param avatar_id: The ID of the avatar or camera.
        """

        if avatar_id == self._avatar.id:
            self._avatar = None
        # Remove commands for this avatar.
        self._avatar_commands = [cmd for cmd in self._avatar_commands if ("avatar_id" not in cmd) or
                                 (cmd["avatar_id"] != avatar_id)]
        self.communicate({"$type": "destroy_avatar",
                          "avatar_id": avatar_id})

    def _tap(self, object_id: int, arm: Arm) -> TaskStatus:
        """
        Try to tap an object.

        Possible [return values](task_status.md):

        - `success` (The avatar tapped the object.)
        - `too_close_to_reach`
        - `too_far_to_reach`
        - `behind_avatar`
        - `no_longer_bending`
        - `bad_raycast`
        - `failed_to_tap`

        :param object_id: The ID of the object.
        :param arm: The arm.

        :return: A `TaskStatus` indicating whether the avatar tapped the object and if not, why.
        """

        self._start_task()

        # Get the origin of the raycast.
        if arm == Arm.left:
            origin = np.array(self._avatar.frame.get_mitten_center_left_position())
        else:
            origin = self._avatar.frame.get_mitten_center_right_position()

        success, target = self._get_raycast_point(object_id=object_id, origin=np.array(origin), forward=0.01)

        # The raycast didn't hit the target.
        if not success:
            return TaskStatus.bad_raycast

        angle = get_angle_between(v1=FORWARD, v2=self._avatar.frame.get_forward())
        target = rotate_point_around(point=target - self._avatar.frame.get_position(), angle=-angle)

        # Couldn't bend the arm to the target.
        reach_status = self.reach_for_target(target=TDWUtils.array_to_vector3(target), arm=arm)
        if reach_status != TaskStatus.success:
            return reach_status

        # Tap the object.
        p = target + np.array(self._avatar.frame.get_forward()) * 1.1
        self.reach_for_target(target=TDWUtils.array_to_vector3(p), arm=arm, check_if_possible=False, do_motion=False)
        # Get the mitten ID.
        mitten_id = 0
        for o_id in self._avatar.body_parts_static:
            if self._avatar.body_parts_static[o_id].name == f"mitten_{arm.name}":
                mitten_id = o_id
                break
        # Let the arm bend until the mitten collides with the object.
        mitten_collision = False
        count = 0
        while not mitten_collision and count < 200:
            self.communicate([])
            if object_id in self.frames[-1].avatar_object_collisions[mitten_id]:
                mitten_collision = True
                break
            count += 1
        self.reset_arms()
        self._avatar.status = TaskStatus.idle
        if mitten_collision:
            return TaskStatus.success
        else:
            return TaskStatus.failed_to_tap

    def end(self) -> None:
        """
        End the simulation. Terminate the build process.
        """

        self.communicate({"$type": "terminate"})

    def _get_position(self, target: Union[np.array, int]) -> np.array:
        """
        Convert the target to a numpy array. If the target is an object ID, get the object's position.

        :param target: The target position or object.

        :return: The position.
        """

        # This is an object ID.
        if isinstance(target, int):
            if target not in self.static_object_info:
                raise Exception(f"Object not found: {target}")
            return self._get_raycast_point(object_id=target, origin=np.array(self._avatar.frame.get_position()))[1]
        elif isinstance(target, dict):
            return TDWUtils.vector3_to_array(target)
        else:
            return target

    def _get_raycast_point(self, object_id: int, origin: np.array, forward: float = 0.2) -> (bool, np.array):
        """
        Raycast to a target object from the avatar.

        :param object_id: The object ID.
        :param forward: Extend the origin along the avatar's forward directional vector by this length.

        :return: The point of the raycast hit and whether the raycast hit the object.
        """

        resp = self.communicate({"$type": "send_bounds",
                                 "ids": [object_id],
                                 "frequency": "once"})
        bounds = get_data(resp=resp, d_type=Bounds)
        # Raycast to the center of the bounds to get the nearest point.
        destination = TDWUtils.array_to_vector3(bounds.get_center(0))
        # Add a forward directional vector.
        origin += np.array(self._avatar.frame.get_forward()) * forward
        origin[1] = destination["y"]
        resp = self.communicate({"$type": "send_raycast",
                                 "origin": TDWUtils.array_to_vector3(origin),
                                 "destination": destination})
        raycast = get_data(resp=resp, d_type=Raycast)
        point = np.array(raycast.get_point())
        return raycast.get_hit() and raycast.get_object_id() is not None and raycast.get_object_id() == object_id, point

    def _get_audio_commands(self) -> List[dict]:
        """
        :return: A list of audio commands generated from `self.frame_data`
        """

        commands = []
        if self._audio_playback_mode is None:
            return commands
        if self._audio_playback_mode == "unity":
            cmd = "play_audio_data"
        elif self._audio_playback_mode == "resonance_audio":
            cmd = "play_point_source_data"
        else:
            raise Exception(f"Bad audio playback type: {self._audio_playback_mode}")
        if len(self.frames) == 0:
            return commands

        for audio, object_id in self.frames[-1].audio:
            if audio is None:
                continue
            commands.append({"$type": cmd,
                             "id": object_id,
                             "num_frames": audio.length,
                             "num_channels": 1,
                             "frame_rate": 44100,
                             "wav_data": audio.wav_str,
                             "y_pos_offset": 0.1})
        return commands

    def _get_scene_init_commands_early(self) -> List[dict]:
        """
        Get commands to initialize the scene before adding avatars.

        :return: A list of commands to initialize the scene. Override this function for a different "scene recipe".
        """

        return [{"$type": "load_scene",
                 "scene_name": "ProcGenScene"},
                TDWUtils.create_empty_room(12, 12)]

    def _do_scene_init_late(self) -> None:
        """
        Initialize the scene after adding avatars.
        """

        return

    def _init_avatar(self) -> None:
        """
        Initialize the avatar.
        """

        self._create_avatar(avatar_id="a")

    def _get_avatar_status(self) -> TaskStatus:
        """
        Get the avatar's status and set the status to `idle`.

        :return: The avatar's status.
        """

        status = self._avatar.status
        self._avatar.status = TaskStatus.idle
        return status

    def _start_task(self) -> None:
        """
        Start a new task. Clear frame data and task status.
        """

        self.frames.clear()
