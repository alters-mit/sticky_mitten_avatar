from csv import DictReader
from json import loads
from pathlib import Path
import random
import numpy as np
from pkg_resources import resource_filename
from typing import Dict, List, Union, Optional, Tuple
from tdw.floorplan_controller import FloorplanController
from tdw.tdw_utils import TDWUtils, QuaternionUtils
from tdw.output_data import Bounds, Rigidbodies, SegmentationColors, Raycast, CompositeObjects, Overlap, Transforms,\
    Version
from tdw.py_impact import AudioMaterial, PyImpact, ObjectInfo
from tdw.object_init_data import AudioInitData
from tdw.release.pypi import PyPi
from sticky_mitten_avatar.avatars import Arm, Baby
from sticky_mitten_avatar.avatars.avatar import Avatar, Joint, BodyPartStatic
from sticky_mitten_avatar.util import get_data, get_angle, rotate_point_around, get_angle_between, FORWARD, \
    OCCUPANCY_CELL_SIZE
from sticky_mitten_avatar.paths import SPAWN_POSITIONS_PATH, OCCUPANCY_MAP_DIRECTORY, SCENE_BOUNDS_PATH, \
    ROOM_MAP_DIRECTORY, Y_MAP_DIRECTORY, TARGET_OBJECTS_PATH, COMPOSITE_OBJECT_AUDIO_PATH, SURFACE_MAP_DIRECTORY
from sticky_mitten_avatar.static_object_info import StaticObjectInfo
from sticky_mitten_avatar.frame_data import FrameData
from sticky_mitten_avatar.task_status import TaskStatus


class StickyMittenAvatarController(FloorplanController):
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
    segmentation_colors = c.frame.id_pass

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

    - `frame` Dynamic data for all of the most recent frame (i.e. the frame after doing an action such as `reach_for_target()`). [Read this](frame_data.md) for a full API.

    ```python
    # Get the segmentation colors and depth map from the most recent frame.
    id_pass = c.frame.id_pass
    depth_pass = c.frame.depth_pass
    # etc.
    ```

    - `static_object_data`: Static info for all objects in the scene. [Read this](static_object_info.md) for a full API.

    ```python
    # Get the segmentation color of an object.
    segmentation_color = c.static_object_info[object_id].segmentation_color
    ```

    - `static_avatar_data` Static info for the avatar's body parts. [Read this](body_part_static.md) for a full API. Key = body part ID.

    ```python
    for body_part_id in c.static_avatar_data:
        body_part = c.static_avatar_data[body_part_id]
        print(body_part.object_id) # The object ID of the body part (matches body_part_id).
        print(body_part.color) # The segmentation color.
        print(body_part.name) # The name of the body part.
    ```

    - `occupancy_map` A numpy array of positions in the scene and whether they are occupied.
       If `scene` or `layout` is None, then this is None.
       Shape is `(width, length)` Data type = `int`. 0 = occupied. 1 = free. 2 = outside of the scene.
       A position is occupied if there is an object (such as a table) or environment obstacle (such as a wall) within 0.25 meters of the position.

       This is static data for the _initial_ scene occupancy_maps. It won't update if an object's position changes.

       Convert from the coordinates in the array to an actual position using `get_occupancy_position()`.

    ```python
    c.init_scene(scene="2a", layout=1)

    print(c.occupancy_map[37][16]) # 0 (occupied)
    print(c.get_occupancy_position(37, 16)) # (True, -1.5036439895629883, -0.42542076110839844)
    ```

    - `goal_positions` A dictionary of possible goal positions.
      Format: `{room_index: "model_name": [pos0, pos1, pos2]}`

    ```python
    c.init_scene(scene="2a", layout=1)

    print(c.goal_positions[0]) # [-10.25364399   0.49080563  -1.42542076]
    ```

    ## Functions

    """

    # A high drag value to stop movement.
    _STOP_DRAG = 1000

    def __init__(self, port: int = 1071, launch_build: bool = True, demo: bool = False, id_pass: bool = True,
                 audio: bool = False, screen_width: int = 256, screen_height: int = 256):
        """
        :param port: The port number.
        :param launch_build: If True, automatically launch the build.
        :param demo: If True, this is a demo controller. The build will play back audio and set a slower framerate and physics time step.
        :param id_pass: If True, add the segmentation color pass to the [`FrameData`](frame_data.md). The simulation will run somewhat slower.
        :param audio: If True, include audio data in the FrameData.
        :param screen_width: The width of the screen in pixels.
        :param screen_height: The height of the screen in pixels.
        """

        self._id_pass = id_pass
        self._audio = audio

        self._container_shapes = loads(Path(resource_filename(__name__, "object_data/container_shapes.json")).
                                       read_text(encoding="utf-8"))
        # Cache the entities.
        self._avatar: Optional[Avatar] = None

        # Create an empty occupancy map.
        self.occupancy_map: Optional[np.array] = None
        self._scene_bounds: Optional[dict] = None
        self.goal_positions: Optional[dict] = None
        # The IDs of each target object.
        self._target_object_ids: List[int] = list()

        # Commands sent by avatars.
        self._avatar_commands: List[dict] = []
        # Cache static data.
        self.static_object_info: Dict[int, StaticObjectInfo] = dict()
        self.static_avatar_info: Dict[int, BodyPartStatic] = dict()
        self._demo = demo
        # Load default audio values for objects.
        self._default_audio_values = PyImpact.get_object_info()
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
                     "sleep_threshold": 0.1},
                    {"$type": "set_screen_size",
                     "width": screen_width,
                     "height": screen_height},
                    {"$type": "send_version"}]
        # Set the frame rate and timestep for audio.
        if self._demo:
            commands.extend([{"$type": "set_target_framerate",
                             "framerate": 30},
                             {"$type": "set_time_step",
                              "time_step": 0.02}])
        resp = self.communicate(commands)

        # Make sure that the build is the correct version.
        if not launch_build:
            version = get_data(resp=resp, d_type=Version)
            build_version = version.get_tdw_version()
            python_version = PyPi.get_installed_tdw_version(truncate=True)
            if build_version != python_version:
                print(f"Your installed version of tdw ({python_version} doesn't match the version of the build "
                      f"{build_version}. This might cause errors!")

    def init_scene(self, scene: str = None, layout: int = None, room: int = -1) -> None:
        """
        Initialize a scene, populate it with objects, add the avatar, and set rendering options.
        The controller by default will load a simple empty room:

        ```python
        from sticky_mitten_avatar import StickyMittenAvatarController

        c = StickyMittenAvatarController()
        c.init_scene()
        ```

        Set the `scene` and `layout` parameters in `init_scene()` to load an interior scene with furniture and props.
        Set the `room` to spawn the avatar in the center of a room.

        ```python
        from sticky_mitten_avatar import StickyMittenAvatarController

        c = StickyMittenAvatarController()
        c.init_scene(scene="2b", layout=0, room=1)
        ```

        Valid scenes, layouts, and rooms:

        | `scene` | `layout` | `room` |
        | --- | --- | --- |
        | 1a, 1b, or 1c | 0, 1, or 2 | 0, 1, 2, 3, 4, 5, 6 |
        | 2a, 2b, or 2c | 0, 1, or 2 | 0, 1, 2, 3, 4, 5, 6, 7, 8 |
        | 4a, 4b, or 4c | 0, 1, or 2 | 0, 1, 2, 3, 4, 5, 6, 7 |
        | 5a, 5b, or 5c | 0, 1, or 2 | 0, 1, 2, 3 |

        :param scene: The name of an interior floorplan scene. If None, the controller will load a simple empty room.
        :param layout: The furniture layout of the floorplan. If None, the controller will load a simple empty room.
        :param room: The index of the room that the avatar will spawn in the center of. If `scene` or `layout` is None, the avatar will spawn in at (0, 0, 0). If `room == -1` the room will be chosen randomly.
        """

        # Initialize the scene.
        self.communicate(self._get_scene_init_commands(scene=scene, layout=layout))

        # Create the avatar.
        self._init_avatar()

        commands = [{"$type": "send_collisions",
                     "enter": True,
                     "stay": False,
                     "exit": False,
                     "collision_types": ["obj", "env"]},
                    {"$type": "send_segmentation_colors",
                     "frequency": "once"},
                    {"$type": "send_composite_objects",
                     "frequency": "once"},
                    {"$type": "send_rigidbodies",
                     "frequency": "once"},
                    {"$type": "send_transforms",
                     "frequency": "once"},
                    {"$type": "send_bounds",
                     "frequency": "once"}]

        # Teleport the avatar to a room.
        if scene is not None and layout is not None and room is not None:
            rooms = loads(SPAWN_POSITIONS_PATH.read_text())[scene[0]][str(layout)]
            if room == -1:
                room = random.randint(0, len(rooms) - 1)
            assert 0 <= room < len(rooms), f"Invalid room: {room}"
            commands.append({"$type": "teleport_avatar_to",
                             "avatar_id": "a",
                             "position": rooms[room]})

        # Request SegmentationColors and CompositeObjects for this frame only.
        resp = self.communicate(commands)
        # Parse composite object audio data.
        segmentation_colors = get_data(resp=resp, d_type=SegmentationColors)
        # Get the name of each object.
        object_names: Dict[int, str] = dict()
        for i in range(segmentation_colors.get_num()):
            object_names[segmentation_colors.get_object_id(i)] = segmentation_colors.get_object_name(i)

        composite_objects = get_data(resp=resp, d_type=CompositeObjects)
        composite_object_audio: Dict[int, ObjectInfo] = dict()
        # Get the audio values per sub object.
        composite_object_json = loads(COMPOSITE_OBJECT_AUDIO_PATH.read_text( encoding="utf-8"))
        for i in range(composite_objects.get_num()):
            composite_object_id = composite_objects.get_object_id(i)
            composite_object_data = composite_object_json[object_names[composite_object_id]]
            for j in range(composite_objects.get_num_sub_objects(i)):
                sub_object_id = composite_objects.get_sub_object_id(i, j)
                sub_object_name = object_names[sub_object_id]
                # Add the audio data to the dictionary.
                composite_object_audio[sub_object_id] = ObjectInfo(
                    name=sub_object_name,
                    amp=composite_object_data[sub_object_name]["amp"],
                    mass=composite_object_data[sub_object_name]["mass"],
                    bounciness=composite_object_data[sub_object_name]["bounciness"],
                    library=composite_object_data[sub_object_name]["library"],
                    material=AudioMaterial[composite_object_data[sub_object_name]["material"]],
                    resonance=composite_object_data[sub_object_name]["resonance"])

        # Cache the static object data.
        rigidbodies = get_data(resp=resp, d_type=Rigidbodies)
        bounds = get_data(resp=resp, d_type=Bounds)
        for i in range(segmentation_colors.get_num()):
            object_id = segmentation_colors.get_object_id(i)
            # Add audio data for either the root object or a sub-object.
            if object_id in composite_object_audio:
                object_audio = composite_object_audio[object_id]
            elif object_id in self._audio_values:
                object_audio = self._audio_values[object_id]
            else:
                object_audio = self._default_audio_values[segmentation_colors.get_object_name(i).lower()]

            static_object = StaticObjectInfo(object_id=object_id,
                                             segmentation_colors=segmentation_colors,
                                             rigidbodies=rigidbodies,
                                             audio=object_audio,
                                             bounds=bounds,
                                             target_object=object_id in self._target_object_ids)
            self.static_object_info[static_object.object_id] = static_object
        self._end_task()

    def _end_task(self) -> None:
        """
        End the task and update the frame data.
        """

        commands = []
        if not self._demo:
            commands.append({"$type": "toggle_image_sensor",
                             "sensor_name": "SensorContainer",
                             "avatar_id": self._avatar.id})
        # Request output data to update the frame data.
        commands.extend([{"$type": "send_images",
                          "frequency": "once"},
                         {"$type": "send_rigidbodies",
                          "frequency": "once"},
                         {"$type": "send_transforms",
                          "frequency": "once"},
                         {"$type": "send_camera_matrices",
                          "frequency": "once"}])

        resp = self.communicate(commands)
        # Update the frame data.
        self.frame = FrameData(resp=resp, objects=self.static_object_info, avatar=self._avatar, audio=self._audio)

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

        if self._id_pass:
            pass_masks = ["_img", "_id", "_depth"]
        else:
            pass_masks = ["_img", "_depth"]
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
                         {"$type": "set_avatar_drag",
                          "drag": self._STOP_DRAG,
                          "angular_drag": self._STOP_DRAG,
                          "avatar_id": avatar_id},
                         {"$type": "set_pass_masks",
                          "pass_masks": pass_masks,
                          "avatar_id": avatar_id},
                         {"$type": "toggle_image_sensor",
                          "sensor_name": "FollowCamera",
                          "avatar_id": avatar_id}])
        if not self._demo:
            commands.append({"$type": "toggle_image_sensor",
                             "sensor_name": "SensorContainer",
                             "avatar_id": avatar_id})
        # Set all sides of both mittens to be sticky.
        for sub_mitten in ["palm", "back", "side"]:
            for is_left in [True, False]:
                commands.append({"$type": "set_stickiness",
                                 "sub_mitten": sub_mitten,
                                 "sticky": True,
                                 "is_left": is_left,
                                 "avatar_id": avatar_id,
                                 "show": False})

        if self._demo:
            commands.append({"$type": "add_audio_sensor",
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

        # Set the joint values profile.
        commands.append(self._avatar.get_default_sticky_mitten_profile())

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

        # Update the avatar. Add new avatar commands for the next frame.
        if self._avatar is not None:
            self._avatar_commands.extend(self._avatar.on_frame(resp=resp))

        return resp

    def _add_object(self, model_name: str, position: Dict[str, float] = None,
                    rotation: Dict[str, float] = None, library: str = "models_core.json",
                    scale: Dict[str, float] = None, audio: ObjectInfo = None) -> Tuple[int, List[dict]]:
        """
        Add an object to the scene.

        :param model_name: The name of the model.
        :param position: The position of the model.
        :param rotation: The starting rotation of the model. Can be Euler angles or a quaternion.
        :param library: The path to the records file. If left empty, the default library will be selected.
                        See `ModelLibrarian.get_library_filenames()` and `ModelLibrarian.get_default_library()`.
        :param scale: The scale factor of the object. If None, the scale factor is (1, 1, 1)
        :param audio: Audio values for the object. If None, use default values.

        :return: Tuple: The object ID; A list of commands to create the object.
        """

        init_data = AudioInitData(name=model_name, position=position, rotation=rotation, scale_factor=scale,
                                  audio=audio, library=library)
        object_id, commands = init_data.get_commands()
        if audio is None:
            audio = self._default_audio_values[model_name]
        self._audio_values[object_id] = audio

        return object_id, commands

    def reach_for_target(self, arm: Arm, target: Dict[str, float], do_motion: bool = True,
                         check_if_possible: bool = True, stop_on_mitten_collision: bool = True,
                         precision: float = 0.05) -> TaskStatus:
        """
        Bend an arm joints of an avatar to reach for a target position.

        Possible [return values](task_status.md):

        - `success` (The avatar's arm's mitten reached the target position.)
        - `too_close_to_reach`
        - `too_far_to_reach`
        - `behind_avatar`
        - `no_longer_bending`
        - `mitten_collision` (If `stop_if_mitten_collision == True`)

        :param arm: The arm (left or right).
        :param target: The target position for the mitten relative to the avatar.
        :param do_motion: If True, advance simulation frames until the pick-up motion is done.
        :param stop_on_mitten_collision: If true, the arm will stop bending if the mitten collides with an object other than the target object.
        :param check_if_possible: If True, before bending the arm, check if the mitten can reach the target assuming no obstructions; if not, don't try to bend the arm.
        :param precision: The precision of the action. If the mitten is this distance or less away from the target position, the action returns `success`.

        :return: A `TaskStatus` indicating whether the avatar can reach the target and if not, why.
        """

        self._start_task()

        target = TDWUtils.vector3_to_array(target)

        # Check if it is possible for the avatar to reach the target.
        if check_if_possible:
            status = self._avatar.can_reach_target(target=target, arm=arm)
            if status != TaskStatus.success:
                self._end_task()
                return status

        self._avatar_commands.extend(self._avatar.reach_for_target(arm=arm,
                                                                   target=target,
                                                                   stop_on_mitten_collision=stop_on_mitten_collision,
                                                                   precision=precision))
        self._avatar.status = TaskStatus.ongoing
        if do_motion:
            self._do_joint_motion()
        self._end_task()
        return self._get_avatar_status()

    def grasp_object(self, object_id: int, arm: Arm, do_motion: bool = True, check_if_possible: bool = True,
                     stop_on_mitten_collision: bool = True) -> TaskStatus:
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
        - `mitten_collision` (If `stop_if_mitten_collision == True`)

        :param object_id: The ID of the target object.
        :param do_motion: If True, advance simulation frames until the pick-up motion is done.
        :param arm: The arm of the mitten that will try to grasp the object.
        :param stop_on_mitten_collision: If true, the arm will stop bending if the mitten collides with an object.
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
                self._end_task()
                return TaskStatus.bad_raycast
            reachable_target = self._avatar.get_rotated_target(target=target)
            status = self._avatar.can_reach_target(target=reachable_target, arm=arm)
            if status != TaskStatus.success:
                self._end_task()
                return status

        # Get commands to pick up the target.
        commands = self._avatar.grasp_object(object_id=object_id, target=target, arm=arm,
                                             stop_on_mitten_collision=stop_on_mitten_collision)

        self._avatar_commands.extend(commands)
        self._avatar.status = TaskStatus.ongoing
        if do_motion:
            self._do_joint_motion()
        # The avatar failed to reach the target.
        if self._avatar.status != TaskStatus.success:
            self._end_task()
            return self._get_avatar_status()

        # Return whether the avatar picked up the object.
        self._avatar.status = TaskStatus.idle
        if self._avatar.is_holding(object_id=object_id):
            self._end_task()
            return TaskStatus.success
        else:
            self._end_task()
            return TaskStatus.failed_to_pick_up

    def drop(self, arm: Arm, reset_arm: bool = True, do_motion: bool = True) -> TaskStatus:
        """
        Drop any held objects held by the arm. Reset the arm to its neutral position.

        Possible [return values](task_status.md):

        - `success` (The avatar's arm dropped all objects held by the arm.)

        :param arm: The arm that will drop any held objects.
        :param reset_arm: If True, reset the arm's positions to "neutral".
        :param do_motion: If True, advance simulation frames until the pick-up motion is done.
        """

        self._start_task()

        self._avatar_commands.extend(self._avatar.drop(reset=reset_arm, arm=arm))
        if do_motion:
            self._do_joint_motion()
        self._end_task()
        return TaskStatus.success

    def reset_arm(self, arm: Arm, do_motion: bool = True) -> TaskStatus:
        """
        Reset an avatar's arm to its neutral positions.

        Possible [return values](task_status.md):

        - `success` (The avatar's arm reset.)

        :param arm: The arm that will be reset.
        :param do_motion: If True, advance simulation frames until the pick-up motion is done.
        """

        self._start_task()

        self._avatar_commands.extend(self._avatar.reset_arm(arm=arm))
        if do_motion:
            self._do_joint_motion()
        self._end_task()
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
        self._end_task()
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
            # Arrived at the correct alignment.
            if np.abs(angle) < stopping_threshold or ((initial_angle < 0 and angle > 0) or
                                                      (initial_angle > 0 and angle < 0)):
                return TaskStatus.success, angle

            return TaskStatus.ongoing, angle
        # Set the target to the object's position.
        if isinstance(target, int):
            target = self.frame.object_transforms[target].position
        # Convert the Vector3 target to a numpy array.
        else:
            target = TDWUtils.vector3_to_array(target)
        target[1] = 0
        self._start_task()

        # Get the angle to the target.
        initial_angle = get_angle(origin=np.array(self._avatar.frame.get_position()),
                                  forward=np.array(self._avatar.frame.get_forward()),
                                  position=target)
        # Decide the shortest way to turn.
        if initial_angle > 0:
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
              turn_stopping_threshold: float = 0.15, move_stopping_threshold: float = 0.35,
              stop_on_collision: bool = True, turn: bool = True) -> TaskStatus:
        """
        Move the avatar to a target position or object.

        Possible [return values](task_status.md):

        - `success` (The avatar arrived at the target.)
        - `too_long`
        - `overshot`
        - `collided_with_something_heavy` (if `stop_on_collision == True`)
        - `collided_with_environment` (if `stop_on_collision == True`)

        :param target: Either the target position or the ID of the target object.
        :param turn_force: The force at which the avatar will turn. More force = faster, but might overshoot the target.
        :param turn_stopping_threshold: Stop when the avatar is within this many degrees of the target.
        :param move_force: The force at which the avatar will move. More force = faster, but might overshoot the target.
        :param move_stopping_threshold: Stop within this distance of the target.
        :param stop_on_collision: If True, stop moving when the object collides with a large object (mass > 90) or the environment (e.g. a wall).
        :param turn: If True, try turning to face the target before moving.

        :return:  A `TaskStatus` indicating whether the avatar arrived at the target and if not, why.
        """

        def _get_state() -> TaskStatus:
            """
            :return: Whether the avatar is at its destination, overshot it, or still going to it.
            """

            # Check if the root object of the avatar collided with anything large. If so, stop movement.
            if stop_on_collision:
                if self._avatar.base_id in self._avatar.collisions:
                    for o_id in self._avatar.collisions[self._avatar.base_id]:
                        collidee_mass = self.static_object_info[o_id].mass
                        if collidee_mass >= 90:
                            return TaskStatus.collided_with_something_heavy
                # If the avatar's body collided with the environment (e.g. a wall), stop movement.
                for self._avatar.base_id in self._avatar.env_collisions:
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

        # Set the target. If it's an object, the target is the nearest point on the bounds.
        if isinstance(target, int):
            if self.frame is None:
                self.communicate([])
            target = self.frame.object_transforms[target].position
        # Convert the Vector3 target to a numpy array.
        elif isinstance(target, dict):
            target = TDWUtils.vector3_to_array(target)

        self._start_task()

        initial_position = self._avatar.frame.get_position()

        # Get the distance to the target.
        initial_distance = np.linalg.norm(np.array(initial_position) - target)

        if turn:
            # Turn to the target.
            status = self.turn_to(target=TDWUtils.array_to_vector3(target), force=turn_force,
                                  stopping_threshold=turn_stopping_threshold)
            if status != TaskStatus.success:
                self._stop_avatar()
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

    def move_forward_by(self, distance: float, move_force: float = 80, move_stopping_threshold: float = 0.35,
                        stop_on_collision: bool = True) -> TaskStatus:
        """
        Move the avatar forward by a distance along the avatar's current forward directional vector.

        Possible [return values](task_status.md):

        - `success` (The avatar moved forward by the distance.)
        - `too_long`
        - `overshot`
        - `collided_with_something_heavy` (if `stop_on_collision == True`)
        - `collided_with_environment` (if `stop_on_collision == True`)

        :param distance: The distance that the avatar will travel. If < 0, the avatar will move backwards.
        :param move_force: The force at which the avatar will move. More force = faster, but might overshoot the target.
        :param move_stopping_threshold: Stop within this distance of the target.
        :param stop_on_collision: If True, stop moving when the object collides with a large object (mass > 90) or the environment (e.g. a wall).

        :return: A `TaskStatus` indicating whether the avatar moved forward by the distance and if not, why.
        """

        # The target is at `distance` away from the avatar's position along the avatar's forward directional vector.
        target = np.array(self._avatar.frame.get_position()) + (np.array(self._avatar.frame.get_forward()) * distance)
        return self.go_to(target=target, move_force=move_force, move_stopping_threshold=move_stopping_threshold,
                          stop_on_collision=stop_on_collision, turn=False)

    def shake(self, joint_name: str = "elbow_left", axis: str = "pitch", angle: Tuple[float, float] = (20, 30),
              num_shakes: Tuple[int, int] = (3, 5), force: Tuple[float, float] = (900, 1000)) -> TaskStatus:
        """
        Shake an avatar's arm for multiple iterations.
        Per iteration, the joint will bend forward by an angle and then bend back by an angle.
        The motion ends when all of the avatar's joints have stopped moving.

        Possible [return values](task_status.md):

        - `success`
        - `bad_joint`

        :param joint_name: The name of the joint.
        :param axis: The axis of the joint's rotation.
        :param angle: Each shake will bend the joint by a angle in degrees within this range.
        :param num_shakes: The avatar will shake the joint a number of times within this range.
        :param force: The avatar will add strength to the joint by a value within this range.

        :return: A `TaskStatus` indicating whether the avatar shook the joint and if not, why.
        """

        self._start_task()

        # Check if the joint and axis are valid.
        joint: Optional[Joint] = None
        for j in Avatar.JOINTS:
            if j.joint == joint_name and j.axis == axis:
                joint = j
                break
        if joint is None:
            return TaskStatus.bad_joint

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
        self._end_task()
        return TaskStatus.success

    def put_in_container(self, object_id: int, container_id: int, arm: Arm) -> TaskStatus:
        """
        Try to put an object in a container.
        Combines the following functions:

        1. `grasp_object(object_id, arm`) if the avatar isn't already grasping the object.
        2. `reach_for_target(position, arm)` where `position` is a point above the container.
        3. `drop(arm)`

        Possible [return values](task_status.md):

        - `success` (The avatar put the object in the container.)
        - `too_close_to_reach` (Either the object or the container is too close.)
        - `too_far_to_reach` (Either the object or the container is too far away.)
        - `behind_avatar` (Either the object or the container is behind the avatar.)
        - `no_longer_bending` (While trying to grasping the object.)
        - `failed_to_pick_up` (After trying to grasp the object.)
        - `bad_raycast` (Before trying to grasp the object.)
        - `mitten_collision` (Only while trying to grasp the object.)
        - `not_in_container`
        - `not_a_container`

        :param object_id: The ID of the object that the avatar will try to put in the container.
        :param container_id: The ID of the container. To determine if an object is a container, see [`StaticObjectInfo.container')(static_object_info.md).
        :param arm: The arm that will try to pick up the object.

        :return: A `TaskStatus` indicating whether the avatar put the object in the container and if not, why.
        """

        if not self.static_object_info[container_id].container:
            return TaskStatus.not_a_container

        self._start_task()

        # Grasp the object.
        if object_id not in self.frame.held_objects[arm]:
            status = self.grasp_object(object_id=object_id, arm=arm)
            if status != TaskStatus.success:
                self._end_task()
                return status
        # Lift the container.
        self.reach_for_target(target={"x": 0.05 if arm == Arm.right else -0.05, "y": 0.15, "z": 0.32},
                              arm=Arm.left if arm == Arm.right else Arm.right,
                              check_if_possible=False,
                              stop_on_mitten_collision=False)
        # Lift up the object.
        self.reach_for_target(target={"x": 0.2 if arm == Arm.right else -0.2, "y": 0.45, "z": 0.2},
                              arm=arm,
                              check_if_possible=False,
                              stop_on_mitten_collision=False)

        # Get the up directional vector.
        up = np.array(QuaternionUtils.get_up_direction(q=tuple(self.frame.object_transforms[container_id].rotation)))
        # Get the height of the container.
        height = self.static_object_info[container_id].size[1]
        # Get a position above the base of the container.
        pos = self.frame.object_transforms[container_id].position

        target = pos + (up * height)
        reachable_target = self._avatar.get_rotated_target(target=target)

        # Raise the target towards the mitten until the avatar can reach it.
        direction_to_mitten = self.frame.avatar_body_part_transforms[self._avatar.mitten_ids[arm]].position - pos
        direction_to_mitten /= np.linalg.norm(direction_to_mitten)
        d = 0
        delta_d = 0.025
        status = self._avatar.can_reach_target(target=reachable_target, arm=arm)
        while status != TaskStatus.success and d < 0.5 and target[1] < 0.5:
            status = self._avatar.can_reach_target(target=reachable_target, arm=arm)
            d += delta_d
            target += direction_to_mitten * delta_d
            reachable_target = self._avatar.get_rotated_target(target=target)
        if status != TaskStatus.success:
            self._end_task()
            return status
        # Reach for the target.
        self.reach_for_target(target=TDWUtils.array_to_vector3(reachable_target),
                              arm=arm,
                              stop_on_mitten_collision=False,
                              check_if_possible=False)

        # Drop the object.
        self.drop(arm=arm, reset_arm=False, do_motion=False)

        # Loop until the object hits something.
        self.communicate({"$type": "send_rigidbodies",
                          "frequency": "always"})
        sleeping = False
        while not sleeping:
            # Advance one frame.
            resp = self.communicate([])
            rigidbodies = get_data(resp=resp, d_type=Rigidbodies)
            # Check if the object stopped moving.
            for i in range(rigidbodies.get_num()):
                if rigidbodies.get_id(i) == object_id:
                    sleeping = rigidbodies.get_sleeping(i) or np.linalg.norm(rigidbodies.get_velocity(i)) < 0.01
                    break
        # Get the current position of the container.
        resp = self.communicate([{"$type": "send_rigidbodies",
                                  "frequency": "never"},
                                 {"$type": "send_transforms",
                                  "frequency": "once"}])
        tr = get_data(resp=resp, d_type=Transforms)
        rot: Optional[np.array] = None
        pos: Optional[np.array] = None
        for i in range(tr.get_num()):
            if tr.get_id(i) == container_id:
                rot = np.array(tr.get_rotation(i))
                pos = np.array(tr.get_position(i))

        # If the container is upside-down, then the object is not in the container.
        up = QuaternionUtils.get_up_direction(rot)
        if up[1] < 0:
            self._end_task()
            return TaskStatus.not_in_container

        # Get the shape of the container.
        name = self.static_object_info[container_id].model_name
        shape = self._container_shapes[name]

        # Check the overlap of the container to see if the object is in that space. If so, it is in the container.
        size = self.static_object_info[container_id].size
        # Set the position to be in the center of the rotated object.
        center = TDWUtils.array_to_vector3(pos + (up * size[1] / 2))
        pos = TDWUtils.array_to_vector3(pos)
        # Decide which overlap shape to use depending on the container shape.
        if shape == "box":
            resp = self.communicate({"$type": "send_overlap_box",
                                     "position": center,
                                     "rotation": TDWUtils.array_to_vector4(rot),
                                     "half_extents": TDWUtils.array_to_vector3(size / 2)})
        elif shape == "sphere":
            resp = self.communicate({"$type": "send_overlap_sphere",
                                     "position": center,
                                     "radius": min(size)})
        elif shape == "capsule":
            resp = self.communicate({"$type": "send_overlap_capsule",
                                     "position": pos,
                                     "end": center,
                                     "radius": min(size)})
        else:
            raise Exception(f"Bad shape for {name}: {shape}")
        overlap = get_data(resp=resp, d_type=Overlap)
        overlap_ids = overlap.get_object_ids()
        if container_id not in overlap_ids or object_id not in overlap_ids:
            self._end_task()
            return TaskStatus.not_in_container
        self._end_task()
        return TaskStatus.success

    def rotate_camera_by(self, pitch: float = 0, yaw: float = 0) -> None:
        """
        Rotate an avatar's camera around each axis.
        The head of the avatar won't visually rotate, as this could put the avatar off-balance.
        Advances the simulation by 1 frame.

        :param pitch: Pitch (nod your head "yes") the camera by this angle, in degrees.
        :param yaw: Yaw (shake your head "no") the camera by this angle, in degrees.
        """

        self._start_task()

        commands = []
        for angle, axis in zip([pitch, yaw], ["pitch", "yaw"]):
            commands.append({"$type": "rotate_sensor_container_by",
                             "axis": axis,
                             "angle": angle,
                             "avatar_id": self._avatar.id})
        self.communicate(commands)
        self._end_task()

    def reset_camera_rotation(self) -> None:
        """
        Reset the rotation of the avatar's camera.
        Advances the simulation by 1 frame.
        """

        self._start_task()

        self.communicate({"$type": "reset_sensor_container_rotation",
                          "avatar_id": self._avatar.id})
        self._end_task()

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
        mitten_id = self._avatar.mitten_ids[arm]
        # Let the arm bend until the mitten collides with the object.
        mitten_collision = False
        count = 0
        while not mitten_collision and count < 200:
            self.communicate([])
            if object_id in self._avatar.collisions[mitten_id]:
                mitten_collision = True
                break
            count += 1
        self.reset_arm(arm=arm)
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

    def get_occupancy_position(self, i: int, j: int) -> Tuple[bool, float, float]:
        """
        Converts the position (i, j) in the occupancy map to (x, z) coordinates.

        :param i: The i coordinate in the occupancy map.
        :param j: The j coordinate in the occupancy map.

        :return: Tuple: True if the position is in the occupancy map; x coordinate; z coordinate.
        """

        if self.occupancy_map is None or self._scene_bounds is None:
            return False, 0, 0,
        x = self._scene_bounds["x_min"] + (i * OCCUPANCY_CELL_SIZE)
        z = self._scene_bounds["z_min"] + (j * OCCUPANCY_CELL_SIZE)
        return True, x, z

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
        if not self._demo:
            return commands
        elif self.frame is None:
            return commands
        # Get audio per collision.
        for audio, object_id in self.frame.audio:
            if audio is None:
                continue
            commands.append({"$type": "play_audio_data",
                             "id": object_id,
                             "num_frames": audio.length,
                             "num_channels": 1,
                             "frame_rate": 44100,
                             "wav_data": audio.wav_str,
                             "y_pos_offset": 0.1})
        return commands

    def _get_scene_init_commands(self, scene: str = None, layout: int = None) -> List[dict]:
        """
        Get commands to initialize the scene before adding avatars.

        :param scene: The name of the scene. Can be None.
        :param layout: The layout index. Can be None.

        :return: A list of commands to initialize the scene. Override this function for a different "scene recipe".
        """

        if scene is not None and layout is not None:
            commands = self.get_scene_init_commands(scene=scene, layout=layout, audio=True)

            self.occupancy_map = np.load(
                str(OCCUPANCY_MAP_DIRECTORY.joinpath(f"{scene[0]}_{layout}.npy").resolve()))
            self._scene_bounds = loads(SCENE_BOUNDS_PATH.read_text())[scene[0]]

            # Procedurally add containers and target objects.
            if scene is not None and layout is not None:
                room_map = np.load(str(ROOM_MAP_DIRECTORY.joinpath(f"{scene[0]}.npy").resolve()))
                ys_map = np.load(str(Y_MAP_DIRECTORY.joinpath(f"{scene[0]}_{layout}.npy").resolve()))

                # Get all "placeable" positions in the room.
                rooms: Dict[int, List[Tuple[int, int]]] = dict()
                for i in range(0, np.amax(room_map)):
                    # Get all free positions in the room.
                    placeable_positions: List[Tuple[int, int]] = list()
                    for ix, iy in np.ndindex(room_map.shape):
                        if room_map[ix][iy] == i:
                            # If this is the floor, add the position.
                            if self.occupancy_map[ix][iy] == 1:
                                placeable_positions.append((ix, iy))
                    if len(placeable_positions) > 0:
                        rooms[i] = placeable_positions

                # Add 0-1 containers per room.
                for room in list(rooms.keys()):
                    # Maybe don't add a container in this room.
                    if random.random() < 0.25:
                        continue

                    # Get a random position in the room.
                    ix, iy = random.choice(rooms[room])

                    # Get the (x, z) coordinates for this position.
                    # The y coordinate is in `ys_map`.
                    free, x, z = self.get_occupancy_position(ix, iy)
                    container_name = random.choice(StaticObjectInfo.CONTAINERS)
                    commands.extend(self._add_object(position={"x": x, "y": ys_map[ix][iy], "z": z},
                                                     rotation={"x": 0, "y": random.uniform(-179, 179), "z": z},
                                                     scale={"x": 0.5, "y": 0.5, "z": 0.5},
                                                     audio=self._default_audio_values[container_name],
                                                     model_name=container_name)[1])
                    # Mark this space as occupied.
                    self.occupancy_map[ix][iy] = 0

                # Pick a room to add target objects.
                target_objects: Dict[str, float] = dict()
                with open(str(TARGET_OBJECTS_PATH.resolve())) as csvfile:
                    reader = DictReader(csvfile)
                    for row in reader:
                        target_objects[row["name"]] = float(row["scale"])
                target_object_names = list(target_objects.keys())

                # Get all positions in the room and shuffle the order.
                target_room_positions = random.choice(list(rooms.values()))
                random.shuffle(target_room_positions)
                # Add the objects.
                for i in range(random.randint(8, 12)):
                    ix, iy = random.choice(target_room_positions)
                    # Get the (x, z) coordinates for this position.
                    # The y coordinate is in `ys_map`.
                    free, x, z = self.get_occupancy_position(ix, iy)
                    target_object_name = random.choice(target_object_names)
                    # Set custom object info for the target objects.
                    audio = ObjectInfo(name=target_object_name, mass=0.1, material=AudioMaterial.ceramic, resonance=0.6,
                                       amp=0.01, library="models_core.json", bounciness=0.5)
                    scale = target_objects[target_object_name]
                    object_id, object_commands = self._add_object(position={"x": x, "y": ys_map[ix][iy], "z": z},
                                                                  rotation={"x": 0, "y": random.uniform(-179, 179),
                                                                            "z": z},
                                                                  scale={"x": scale, "y": scale, "z": scale},
                                                                  audio=audio,
                                                                  model_name=target_object_name)
                    self._target_object_ids.append(object_id)
                    commands.extend(object_commands)

                    # Mark this space as occupied.
                    self.occupancy_map[ix][iy] = 0

                # Set the goal positions.
                goal_positions = loads(SURFACE_MAP_DIRECTORY.joinpath(f"{scene[0]}_{layout}.json").
                                       read_text(encoding="utf-8"))
                self.goal_positions = dict()
                for k in goal_positions:
                    self.goal_positions[int(k)] = goal_positions[k]

            return commands

        return [{"$type": "load_scene",
                 "scene_name": "ProcGenScene"},
                TDWUtils.create_empty_room(12, 12)]

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

        if self._demo or self._avatar is None:
            return

        self.communicate({"$type": "toggle_image_sensor",
                          "sensor_name": "SensorContainer",
                          "avatar_id": self._avatar.id})
