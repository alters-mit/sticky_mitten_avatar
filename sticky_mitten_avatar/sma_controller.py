import random
from enum import Enum
import numpy as np
from pkg_resources import resource_filename
from typing import Dict, List, Union, Optional, Tuple
from tdw.controller import Controller
from tdw.tdw_utils import TDWUtils
from tdw.librarian import ModelLibrarian
from tdw.output_data import Bounds, Transforms, Rigidbodies, SegmentationColors, Volumes
from tdw.py_impact import AudioMaterial, PyImpact, ObjectInfo
from sticky_mitten_avatar.avatars import Arm, Baby
from sticky_mitten_avatar.avatars.avatar import Avatar, Joint, BodyPartStatic
from sticky_mitten_avatar.util import get_data, get_angle, get_closest_point_in_bounds, rotate_point_around
from sticky_mitten_avatar.dynamic_object_info import DynamicObjectInfo
from sticky_mitten_avatar.static_object_info import StaticObjectInfo
from sticky_mitten_avatar.frame_data import FrameData


class _TaskState(Enum):
    """
    The state of an avatar's motion.
    """

    ongoing = 1,
    success = 2,
    failure = 4


class StickyMittenAvatarController(Controller):
    """
    High-level API controller for sticky mitten avatars. Use this with the `Baby` and `Adult` avatar classes.
    This controller will cache static data for the avatars (such as segmentation colors) and automatically update
    dynamic data (such as position). The controller also has useful wrapper functions to handle the avatar API.

    ```python
    from tdw.tdw_utils import TDWUtils
    from sticky_mitten_avatar.avatars import Arm
    from sticky_mitten_avatar import StickyMittenAvatarController

    c = StickyMittenAvatarController()

    # Load a simple scene.
    avatar_id = "a"
    avatar_id = c.init_scene()

    # Bend an arm.
    c.bend_arm(avatar_id=avatar_id, target={"x": -0.2, "y": 0.21, "z": 0.385}, arm=Arm.left)

    # Get the segementation color pass for the avatar after bending the arm.
    segmentation_colors = c.frame.images[avatar_id][0]
    ```

    ***

    Fields:

    - `frame` Dynamic data for the current frame, updated per frame. [Read this](frame_data.md) for a full API.
      Note: Most of the avatar API advances the simulation multiple frames.
    ```python
    # Get the segementation color pass for the avatar after bending the arm.
    segmentation_colors = c.frame.images[avatar_id][0]
    ```

    - `static_object_data`: Static info for all objects in the scene. [Read this](static_object_info.md) for a full API.

    ```python
    # Get the segmentation color of an object.
    segmentation_color = c.static_object_info[object_id].segmentation_color
    ```

    - `static_avatar_data` Static info for the body parts of each avatar in the scene.


    ```python
    for avatar_id in c.static_avatar_data.avatars:
        for body_part_id in c.static_avatar_data.avatars[avatar_id]:
            body_part = c.static_avatar_data.avatars[avatar_id][body_part_id]
            print(body_part.o_id) # The object ID of the body part (matches body_part_id).
            print(body_part.color) # The segmentation color.
            print(body_part.name) # The name of the body part.
    ```
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
        self._avatars: Dict[str, Avatar] = dict()
        # Commands sent by avatars.
        self._avatar_commands: List[dict] = []
        # Per-frame object physics info.
        self._dynamic_object_info: Dict[int, DynamicObjectInfo] = dict()
        # Cache static data.
        self.static_object_info: Dict[int, StaticObjectInfo] = dict()
        self.static_avatar_info: Dict[str, Dict[int, BodyPartStatic]] = dict()
        self._surface_material = AudioMaterial.hardwood
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
        self.frame: Optional[FrameData] = None

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
                          "pass_masks": ["_img", "_id"],
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
        self._avatars[avatar_id] = avatar
        self.static_avatar_info[avatar_id] = self._avatars[avatar_id].body_parts_static

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

        # Clear object info.
        self._dynamic_object_info.clear()
        # Update object info.
        tran = get_data(resp=resp, d_type=Transforms)
        rigi = get_data(resp=resp, d_type=Rigidbodies)

        if tran is None or rigi is None:
            return resp

        # Update the frame data.
        self.frame = FrameData(resp=resp, objects=self.static_object_info, surface_material=self._surface_material,
                               avatars=self._avatars)

        for i in range(tran.get_num()):
            o_id = tran.get_id(i)
            self._dynamic_object_info[o_id] = DynamicObjectInfo(o_id=o_id, rigi=rigi, tran=tran, tr_index=i)

        # Update the avatars. Add new avatar commands for the next frame.
        for a_id in self._avatars:
            self._avatar_commands.extend(self._avatars[a_id].on_frame(resp=resp))

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

    def bend_arm(self, avatar_id: str, arm: Arm, target: Dict[str, float], do_motion: bool = True) -> bool:
        """
        Bend an arm of an avatar until the mitten is at the target position.
        If the position is sufficiently out of reach, the arm won't bend.
        Otherwise, the motion continues until the mitten is either at the target position or the arm stops moving.

        :param arm: The arm (left or right).
        :param target: The target position for the mitten relative to the avatar.
        :param avatar_id: The unique ID of the avatar.
        :param do_motion: If True, advance simulation frames until the pick-up motion is done.

        :return: True if the mitten is near the target position.
        """

        target = TDWUtils.vector3_to_array(target)

        if not self._avatars[avatar_id].can_bend_to(target=target, arm=arm):
            return False

        self._avatar_commands.extend(self._avatars[avatar_id].bend_arm(arm=arm, target=target))

        if do_motion:
            self._do_joint_motion()
        return True

    def pick_up(self, avatar_id: str, object_id: int, do_motion: bool = True) -> (bool, Arm):
        """
        Bend the arm of an avatar towards an object. Per frame, try to pick up the object.
        If the position is sufficiently out of reach, the arm won't bend.
        The motion continues until either the object is picked up or the arm stops moving.

        :param object_id: The ID of the target object.
        :param avatar_id: The unique ID of the avatar.
        :param do_motion: If True, advance simulation frames until the pick-up motion is done.

        :return: Tuple: True if the avatar picked up the object, and the arm that is picking up the object.
        """

        # Get the bounds of the object.
        resp = self.communicate({"$type": "send_bounds",
                                 "frequency": "once",
                                 "ids": [object_id]})
        bounds = get_data(resp=resp, d_type=Bounds)
        commands, arm = self._avatars[avatar_id].pick_up(bounds=bounds, object_id=object_id)
        self._avatar_commands.extend(commands)

        if do_motion:
            self._do_joint_motion()

        return self._avatars[avatar_id].is_holding(object_id=object_id)

    def put_down(self, avatar_id: str, reset_arms: bool = True, do_motion: bool = True) -> None:
        """
        Begin to put down all objects.
        The motion continues until the arms have reset to their neutral positions.

        :param avatar_id: The unique ID of the avatar.
        :param reset_arms: If True, reset arm positions to "neutral".
        :param do_motion: If True, advance simulation frames until the pick-up motion is done.
        """

        self._avatar_commands.extend(self._avatars[avatar_id].put_down(reset_arms=reset_arms))
        if do_motion:
            self._do_joint_motion()

    def reset_arms(self, avatar_id: str, do_motion: bool = True) -> None:
        """
        Reset the avatar's arm joint positions.
        The motion continues until the arms have reset to their neutral positions.

        :param avatar_id: The ID of the avatar.
        :param do_motion: If True, advance simulation frames until the pick-up motion is done.
        """

        self._avatar_commands.extend(self._avatars[avatar_id].reset_arms())
        if do_motion:
            self._do_joint_motion()

    def _do_joint_motion(self) -> None:
        """
        Step through the simulation until the joints of all avatars are done moving.
        Useful when you want concurrent action (for example, multiple avatars in the same scene):

        ```python
        c = StickyMittenAvatarController()

        c.create_avatar(avatar_id="a")
        c.create_avatar(avatar_id="b")

        # Tell both avatars to start bending arms to different positions.
        # Set do_motion to False so that the avatars can act at the same time.
        c.bend_arm(avatar_id="a", target=pos_a, arm=Arm.left, do_motion=False)
        c.bend_arm(avatar_id="b", target=pos_b, arm=Arm.left, do_motion=False)

        # Wait until both avatars are done moving.
        self.do_joint_motion()
        ```
        """

        done = False
        while not done:
            done = True
            # The loop is done if the IK goals are done.
            for avatar in self._avatars.values():
                if not avatar.is_ik_done():
                    done = False
            # Keep looping.
            if not done:
                self.communicate([])

    def _stop_avatar(self, avatar_id: str) -> None:
        """
        Advance 1 frame and stop the avatar's movement and turning.

        :param avatar_id: The ID of the avatar.
        """

        self.communicate({"$type": "set_avatar_drag",
                          "drag": self._STOP_DRAG,
                          "angular_drag": self._STOP_DRAG,
                          "avatar_id": avatar_id})

    def turn_to(self, avatar_id: str, target: Union[Dict[str, float], int], force: float = 1000,
                stopping_threshold: float = 0.15) -> bool:
        """
        Turn the avatar to face a target.
        The motion continues until the avatar is either facing the target, overshoots it, or rotates a full 360 degrees.

        :param avatar_id: The unique ID of the avatar.
        :param target: The target position or object ID.
        :param force: The force at which the avatar will turn. More force = faster, but might overshoot the target.
        :param stopping_threshold: Stop when the avatar is within this many degrees of the target.

        :return: True if the avatar succeeded in turning to face the target.
        """

        def _get_turn_state() -> _TaskState:
            """
            :return: Whether avatar succeed, failed, or is presently turning.
            """

            angle = get_angle(origin=np.array(avatar.frame.get_position()),
                              forward=np.array(avatar.frame.get_forward()),
                              position=target)

            # Failure because the avatar turned all the way around without aligning with the target.
            if angle - initial_angle >= 180:
                return _TaskState.failure

            if angle > 180:
                angle -= 360

            # Success because the avatar is facing the target.
            if np.abs(angle) < stopping_threshold:
                return _TaskState.success
            # Overshot the turn. Stop.
            if (direction < 0 and angle >= 0) or (direction > 0 and angle <= 0):
                return _TaskState.success

            return _TaskState.ongoing

        avatar = self._avatars[avatar_id]

        # Set the target if it wasn't already a numpy array (for example, if it's an object ID).
        target = self._get_position(target=target)

        # Get the initial angle to the target.
        initial_angle = get_angle(origin=np.array(avatar.frame.get_position()),
                                  forward=np.array(avatar.frame.get_forward()),
                                  position=np.array(target))
        # Decide which direction to turn.
        if initial_angle > 180:
            direction = -1
        else:
            direction = 1

        # Set a low drag.
        self.communicate({"$type": "set_avatar_drag",
                          "drag": 0,
                          "angular_drag": 0.05,
                          "avatar_id": avatar_id})

        turn_command = {"$type": "turn_avatar_by",
                        "torque": force * direction,
                        "avatar_id": avatar_id}

        # Begin to turn.
        self.communicate(turn_command)
        i = 0
        while i < 200:
            # Coast to a stop.
            coasting = True
            while coasting:
                coasting = np.linalg.norm(avatar.frame.get_angular_velocity()) > 0.3
                state = _get_turn_state()
                if state == _TaskState.success:
                    self._stop_avatar(avatar_id=avatar_id)
                    return True
                elif state == _TaskState.failure:
                    self._stop_avatar(avatar_id=avatar_id)
                    return False
                self.communicate([])

            # Turn.
            self.communicate(turn_command)
            state = _get_turn_state()
            if state == _TaskState.success:
                self._stop_avatar(avatar_id=avatar_id)
                return True
            elif state == _TaskState.failure:
                self._stop_avatar(avatar_id=avatar_id)
                return False
            i += 1
        self._stop_avatar(avatar_id=avatar_id)
        return False

    def turn_by(self, avatar_id: str, angle: float, force: float = 1000,
                stopping_threshold: float = 0.15) -> bool:
        """
        Turn the avatar by an angle.
        The motion continues until the avatar is either facing the target, overshoots it, or rotates a full 360 degrees.

        :param avatar_id: The unique ID of the avatar.
        :param angle: The angle to turn to in degrees. If > 0, turn clockwise; if < 0, turn counterclockwise.
        :param force: The force at which the avatar will turn. More force = faster, but might overshoot the target.
        :param stopping_threshold: Stop when the avatar is within this many degrees of the target.

        :return: True if the avatar succeeded in turning to face the target.
        """

        # Rotate the forward directional vector.
        p0 = self._avatars[avatar_id].frame.get_forward()
        p1 = rotate_point_around(origin=np.array([0, 0, 0]), point=p0, angle=angle)
        # Get a point to look at.
        p1 = np.array(self._avatars[avatar_id].frame.get_position()) + (p1 * 1000)
        return self.turn_to(avatar_id=avatar_id, target=TDWUtils.array_to_vector3(p1), force=force,
                            stopping_threshold=stopping_threshold)

    def go_to(self, avatar_id: str, target: Union[Dict[str, float], int],
              turn_force: float = 1000, turn_stopping_threshold: float = 0.15,
              move_force: float = 80, move_stopping_threshold: float = 0.35) -> bool:
        """
        Move the avatar to a target position or object.
        If the avatar isn't facing the target, it will turn to face it (see `turn_to()`).
        The motion continues until the avatar reaches the destination, or if:

        - The avatar overshot the target.
        - The avatar's body collided with a heavy object (mass >= 90)
        - The avatar collided with part of the environment (such as a wall).

        :param avatar_id: The ID of the avatar.
        :param avatar_id: The unique ID of the avatar.
        :param target: The target position or object ID.
        :param turn_force: The force at which the avatar will turn. More force = faster, but might overshoot the target.
        :param turn_stopping_threshold: Stop when the avatar is within this many degrees of the target.
        :param move_force: The force at which the avatar will move. More force = faster, but might overshoot the target.
        :param move_stopping_threshold: Stop within this distance of the target.

        :return: True if the avatar arrived at the destination.
        """

        def _get_state() -> _TaskState:
            """
            :return: Whether the avatar is at its destination, overshot it, or still going to it.
            """

            # Check if the root object of the avatar collided with anything large. If so, stop movement.
            for body_part_id in avatar.collisions:
                name = avatar.body_parts_static[body_part_id].name
                if name.startswith("A_StickyMitten"):
                    for o_id in avatar.collisions[body_part_id]:
                        collidee_mass = self.static_object_info[o_id].mass
                        if collidee_mass >= 90:
                            print("hit something heavy")
                            return _TaskState.failure
            # If the avatar's body collided with the environment (e.g. a wall), stop movement.
            for body_part_id in avatar.env_collisions:
                name = avatar.body_parts_static[body_part_id].name
                if name.startswith("A_StickyMitten"):
                    return _TaskState.failure

            p = np.array(avatar.frame.get_position())
            d_from_initial = np.linalg.norm(initial_position - p)
            # Overshot. End.
            if d_from_initial > initial_distance:
                return _TaskState.failure
            # We're here! End.
            d = np.linalg.norm(p - target)
            if d <= move_stopping_threshold:
                return _TaskState.success
            # Keep truckin' along.
            return _TaskState.ongoing

        avatar = self._avatars[avatar_id]
        initial_position = avatar.frame.get_position()

        # Set the target. If it's an object, the target is the nearest point on the bounds.
        target = self._get_position(target=target, nearest_on_bounds=True, avatar_id=avatar_id)
        # Get the distance to the target.
        initial_distance = np.linalg.norm(np.array(initial_position) - target)

        # Turn to the target.
        self.turn_to(avatar_id=avatar_id, target=target, force=turn_force, stopping_threshold=turn_stopping_threshold)

        # Go to the target.
        self.communicate({"$type": "set_avatar_drag",
                          "drag": 0.1,
                          "angular_drag": 100,
                          "avatar_id": avatar_id})
        i = 0
        while i < 200:
            # Start gliding.
            self.communicate({"$type": "move_avatar_forward_by",
                              "magnitude": move_force,
                              "avatar_id": avatar_id})
            t = _get_state()
            if t == _TaskState.success:
                self._stop_avatar(avatar_id=avatar_id)
                return True
            elif t == _TaskState.failure:
                self._stop_avatar(avatar_id=avatar_id)
                return False
            # Glide.
            while np.linalg.norm(avatar.frame.get_velocity()) > 0.1:
                self.communicate([])
                t = _get_state()
                if t == _TaskState.success:
                    self._stop_avatar(avatar_id=avatar_id)
                    return True
                elif t == _TaskState.failure:
                    self._stop_avatar(avatar_id=avatar_id)
                    return False
            i += 1
        self._stop_avatar(avatar_id=avatar_id)
        return False

    def move_forward_by(self, avatar_id: str, distance: float, move_force: float = 80,
                        move_stopping_threshold: float = 0.35) -> bool:
        """
        Move the avatar forward by a distance along the avatar's current forward directional vector.
        The motion continues until the avatar reaches the destination, or if:

        - The avatar overshot the target.
        - The avatar's body collided with a heavy object (mass >= 90)
        - The avatar collided with part of the environment (such as a wall).

        :param avatar_id: The ID of the avatar.
        :param distance: The distance that the avatar will travel. If < 0, the avatar will move backwards.
        :param move_force: The force at which the avatar will move. More force = faster, but might overshoot the target.
        :param move_stopping_threshold: Stop within this distance of the target.

        :return: True if the avatar arrived at the destination.
        """
        # The target is at `distance` away from the avatar's position along the avatar's forward directional vector.
        target = np.array(self._avatars[avatar_id].frame.get_position()) + (np.array(self._avatars[avatar_id].
                                                                                     frame.get_forward()) * distance)
        return self.go_to(avatar_id=avatar_id, target=target, move_force=move_force,
                          move_stopping_threshold=move_stopping_threshold)

    def shake(self, avatar_id: str, joint_name: str = "elbow_left", axis: str = "pitch",
              angle: Tuple[float, float] = (20, 30), num_shakes: Tuple[int, int] = (3, 5),
              force: Tuple[float, float] = (900, 1000)) -> None:
        """
        Shake an avatar's arm for multiple iterations.
        Per iteration, the joint will bend forward by an angle and then bend back by an angle.
        The motion ends when all of the avatar's joints have stopped moving.

        :param avatar_id: The ID of the avatar.
        :param joint_name: The name of the joint.
        :param axis: The axis of the joint's rotation.
        :param angle: Each shake will bend the joint by a angle in degrees within this range.
        :param num_shakes: The avatar will shake the joint a number of times within this range.
        :param force: The avatar will add strength to the joint by a value within this range.
        """

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
                           "avatar_id": avatar_id},
                          {"$type": "adjust_joint_damper_by",
                           "delta": -damper,
                           "joint": joint.joint,
                           "axis": joint.axis,
                           "avatar_id": avatar_id}])
        # Do each iteration.
        for i in range(random.randint(num_shakes[0], num_shakes[1])):
            a = random.uniform(angle[0], angle[1])
            # Start the shake.
            self.communicate({"$type": "bend_arm_joint_by",
                              "angle": a,
                              "joint": joint.joint,
                              "axis": joint.axis,
                              "avatar_id": avatar_id})
            for j in range(10):
                self.communicate([])
            # Bend the arm back.
            self.communicate({"$type": "bend_arm_joint_by",
                              "angle": -(a / 2),
                              "joint": joint.joint,
                              "axis": joint.axis,
                              "avatar_id": avatar_id})
            for j in range(50):
                self.communicate([])
            # Apply the motion.
            self._do_joint_motion()
        # Reset the force of the joint.
        self.communicate([{"$type": "adjust_joint_force_by",
                           "delta": -force,
                           "joint": joint.joint,
                           "axis": joint.axis,
                           "avatar_id": avatar_id},
                          {"$type": "adjust_joint_damper_by",
                           "delta": damper,
                           "joint": joint.joint,
                           "axis": joint.axis,
                           "avatar_id": avatar_id}])

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
            for avatar_id in self._avatars:
                commands.append({"$type": "toggle_image_sensor",
                                 "sensor_name": "SensorContainer",
                                 "avatar_id": avatar_id})
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
        if avatar_id in self._avatars:
            self._avatars.pop(avatar_id)
        # Remove commands for this avatar.
        self._avatar_commands = [cmd for cmd in self._avatar_commands if ("avatar_id" not in cmd) or
                                 (cmd["avatar_id"] != avatar_id)]
        self.communicate({"$type": "destroy_avatar",
                          "avatar_id": avatar_id})

    def end(self) -> None:
        """
        End the simulation. Terminate the build process.
        """

        self.communicate({"$type": "terminate"})

    def _get_position(self, target: Union[Dict[str, float], np.array, int],
                      nearest_on_bounds: bool = False, avatar_id: str = None) -> np.array:
        """
        Convert the target to a numpy array. If the target is an object ID, get the object's position.

        :param target: The target position or object.
        :param avatar_id: The ID of the avatar. Used only if `nearest_on_bounds == True` and if `target` is an int.
        :param nearest_on_bounds: If True, `avatar_id is not None`, and `target` is an int, set the target position to
                                  the nearest point on the object bounds from the avatar's position.

        :return: The position.
        """

        # This is an object ID.
        if isinstance(target, int):
            if target not in self._dynamic_object_info:
                raise Exception(f"Object not found: {target}")
            # Get the nearest point from the avatar.
            if nearest_on_bounds and (avatar_id is not None):
                resp = self.communicate({"$type": "send_bounds",
                                         "ids": [target],
                                         "frequency": "once"})
                bounds = get_data(resp=resp, d_type=Bounds)
                return get_closest_point_in_bounds(bounds=bounds,
                                                   origin=self._avatars[avatar_id].frame.get_position(),
                                                   index=0)
            # Get the object's position.
            return self._dynamic_object_info[target].position
        elif isinstance(target, dict):
            return TDWUtils.vector3_to_array(target)
        else:
            return target

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
        if self.frame is None:
            return commands

        for audio, object_id in self.frame.audio:
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
