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
from sticky_mitten_avatar.avatars.avatar import Avatar, BodyPartStatic
from sticky_mitten_avatar.util import get_data, OCCUPANCY_CELL_SIZE, \
    TARGET_OBJECT_MASS, CONTAINER_MASS, CONTAINER_SCALE
from sticky_mitten_avatar.paths import SPAWN_POSITIONS_PATH, OCCUPANCY_MAP_DIRECTORY, SCENE_BOUNDS_PATH, \
    ROOM_MAP_DIRECTORY, Y_MAP_DIRECTORY, TARGET_OBJECTS_PATH, COMPOSITE_OBJECT_AUDIO_PATH, SURFACE_MAP_DIRECTORY, \
    TARGET_OBJECT_MATERIALS_PATH, OBJECT_SPAWN_MAP_DIRECTORY
from sticky_mitten_avatar.static_object_info import StaticObjectInfo
from sticky_mitten_avatar.frame_data import FrameData
from sticky_mitten_avatar.task_status import TaskStatus

import pickle

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
    # See FrameData.save_images() and FrameData.get_pil_images()
    segmentation_colors = c.frame.id_pass

    c.end()
    ```

    ***

    ## Parameter types

    #### Dict[str, float]

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

    The types `Dict`, `Union`, and `List` are in the [`typing` module](https://docs.python.org/3/library/typing.html).

    #### Arm

    All parameters of type `Arm` require you to import the [Arm enum class](arm.md):

    ```python
    from sticky_mitten_avatar import Arm

    print(Arm.left)
    ```

    ***

    ## Fields

    - `frame` Dynamic data for all of the most recent frame (i.e. the frame after doing an action such as `reach_for_target()`). [Read this](frame_data.md) for a full API.

    ```python
    # Get the segmentation colors and depth map from the most recent frame.
    id_pass = c.frame.id_pass
    depth_pass = c.frame.depth_pass
    # etc.
    ```

    - `static_object_info`: Static info for all objects in the scene. [Read this](static_object_info.md) for a full API.

    ```python
    # Get the segmentation color of an object.
    segmentation_color = c.static_object_info[object_id].segmentation_color
    ```

    - `segmentation_color_to_id` A dictionary. Key = a hashable representation of the object's segmentation color.
      Value = The object ID. See `static_object_info` for a dictionary mapped to object ID with additional data.

    ```python
    for hashable_color in c.segmentation_color_to_id:
        object_id = c.segmentation_color_to_id[hashable_color]
    ```
    
      To convert an RGB array to a hashable integer, see: [`TDWUtils.color_to_hashable()`](https://github.com/threedworld-mit/tdw/blob/master/Documentation/python/tdw_utils.md).

    - `static_avatar_info` Static info for the avatar's body parts. [Read this](body_part_static.md) for a full API. Key = body part ID.

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

       This is _not_ a navigation map. If there is a gap between positions, the avatar might still be able to go from one to the other.

       Images of each occupancy map can be found in: `images/occupancy_maps`
       Key: Red = Free position. Blue = Free position where a target object or container can be placed.

       Convert from the coordinates in the array to an actual position using `get_occupancy_position()`.

    ```python
    c.init_scene(scene="2a", layout=1)

    print(c.occupancy_map[37][16]) # 0 (occupied)
    print(c.get_occupancy_position(37, 16)) # (1.5036439895629883, -0.42542076110839844)
    ```

    - `goal_positions` A dictionary of possible goal positions.
      Format: `{room_index: "model_name": [pos0, pos1, pos2]}`

    ```python
    from sticky_mitten_avatar import StickyMittenAvatarController

    c = StickyMittenAvatarController()
    c.init_scene(scene="2a", layout=1)
    for room in c.goal_positions:
        print(f"Room {room}")
        for furniture in c.goal_positions[room]:
            print(furniture, c.goal_positions[room][furniture]) # sofa [[3, 31]]
    ```

    ## Functions

    """

    # A high drag value to stop movement.
    _STOP_DRAG = 1000

    def __init__(self, port: int = 1071, launch_build: bool = True, demo: bool = False, id_pass: bool = True,
                 screen_width: int = 256, screen_height: int = 256, debug: bool = False, train = 0):
        """
        :param port: The port number.
        :param launch_build: If True, automatically launch the build.
        :param demo: If True, this is a demo controller. All frames will be rendered.
        :param id_pass: If True, add the segmentation color pass to the [`FrameData`](frame_data.md). The simulation will run somewhat slower.
        :param screen_width: The width of the screen in pixels.
        :param screen_height: The height of the screen in pixels.
        :param debug: If True, debug mode will be enabled.
        """

        self._debug = debug
        self._id_pass = id_pass
        
        if train == 0:
            self.data_path = resource_filename(__name__, "train_dataset.pkl")
        elif train == 1:
            self.data_path = resource_filename(__name__, "test_dataset.pkl")
        elif train == 2:
            self.data_path = resource_filename(__name__, "generate_dataset.pkl")
        else:
            self.data_path = resource_filename(__name__, "extra.pkl")
        with open(self.data_path, 'rb') as f:
            self.dataset = pickle.load(f)
        self.dataset_n = len(self.dataset)
        self.dataset_id = 0

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
        self.container_masses: Dict[int, float] = dict() 

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

        self.segmentation_color_to_id: Dict[int, int] = dict()

        super().__init__(port=port, launch_build=launch_build)

        # Set image encoding to .jpg
        # Set the highest render quality.
        # Set global physics values.
        commands = [{"$type": "set_img_pass_encoding",
                     "value": False},
                    {"$type": "set_render_quality",
                     "render_quality": 5},
                    {"$type": "set_physics_solver_iterations",
                     "iterations": 16},
                    {"$type": "set_vignette",
                     "enabled": False},
                    {"$type": "set_shadow_strength",
                     "strength": 1.0},
                    {"$type": "set_screen_size",
                     "width": screen_width,
                     "height": screen_height},
                    {"$type": "send_version"}]
        resp = self.communicate(commands)

        # Make sure that the build is the correct version.
        '''if not launch_build:
            version = get_data(resp=resp, d_type=Version)
            build_version = version.get_tdw_version()
            python_version = PyPi.get_installed_tdw_version(truncate=True)
            if build_version != python_version:
                print(f"Your installed version of tdw ({python_version}) doesn't match the version of the build "
                      f"{build_version}. This might cause errors!")
        '''
        
    def init_scene(self, scene: str = None, layout: int = None, room: int = -1, data_id=0) -> None:
        """
        Initialize a scene, populate it with objects, and add the avatar.

        **Always call this function before any other API calls.**

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
        | 1a, 1b, 1c | 0, 1, 2 | 0, 1, 2, 3, 4, 5, 6 |
        | 2a, 2b, 2c | 0, 1, 2 | 0, 1, 2, 3, 4, 5, 6, 7, 8 |
        | 4a, 4b, 4c | 0, 1, 2 | 0, 1, 2, 3, 4, 5, 6, 7 |
        | 5a, 5b, 5c | 0, 1, 2 | 0, 1, 2, 3 |

        You can safely call `init_scene()` more than once to reset the simulation.

        :param scene: The name of an interior floorplan scene. If None, the controller will load a simple empty room. Each number (1, 2, etc.) has a different shape, different rooms, etc. Each letter (a, b, c) is a cosmetically distinct variant with the same floorplan.
        :param layout: The furniture layout of the floorplan. Each number (0, 1, 2) will populate the floorplan with different furniture in different positions. If None, the controller will load a simple empty room.
        :param room: The index of the room that the avatar will spawn in the center of. If `scene` or `layout` is None, the avatar will spawn in at (0, 0, 0). If `room == -1` the room will be chosen randomly.
        """

        # Clear all static info.
        self._target_object_ids: List[int] = list()
        self._avatar_commands: List[dict] = []
        self._audio_values: Dict[int, ObjectInfo] = dict()
        self.static_object_info: Dict[int, StaticObjectInfo] = dict()
        self.segmentation_color_to_id: Dict[int, int] = dict()
        self.demo_object_to_id = {}
        self.demo_id_to_object = {}
        self._cam_commands: Optional[list] = None
        
        #dataset
        #if self.dataset_id == self.dataset_n:
        #    self.dataset_id = 0
        #if data_id > -1:
        dataset_id = data_id % self.dataset_n
        self.data = self.dataset[dataset_id]
        '''else:
            if self.dataset_id == self.dataset_n:
                self.dataset_id = 0
            self.data = self.dataset[self.dataset_id]
            self.dataset_id += 1'''
        scene = self.data['scene']['scene']
        layout = self.data['scene']['layout']
        room = self.data['scene']['room']
        print('scene:', scene, layout, room, data_id) 
        # Initialize the scene.
        resp = self.communicate(self._get_scene_init_commands(scene=scene, layout=layout, room=room))
        self._avatar = Baby(debug=self._debug, resp=resp)
        # Cache the avatar.
        self.static_avatar_info = self._avatar.body_parts_static

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
            object_name = segmentation_colors.get_object_name(i).lower()
            # Add audio data for either the root object or a sub-object.
            if object_id in composite_object_audio:
                object_audio = composite_object_audio[object_id]
            elif object_id in self._audio_values:
                object_audio = self._audio_values[object_id]
            else:
                object_audio = self._default_audio_values[object_name]

            static_object = StaticObjectInfo(object_id=object_id,
                                             segmentation_colors=segmentation_colors,
                                             rigidbodies=rigidbodies,
                                             audio=object_audio,
                                             bounds=bounds,
                                             target_object=object_id in self._target_object_ids)
            self.static_object_info[static_object.object_id] = static_object

        # Fill the segmentation color dictionary and carve into the NavMesh.
        demo_id = 0
        for object_id in self.static_object_info:
            hashable_color = TDWUtils.color_to_hashable(self.static_object_info[object_id].segmentation_color)
            self.segmentation_color_to_id[hashable_color] = object_id
            self.demo_object_to_id[object_id] = demo_id
            self.demo_id_to_object[demo_id] = object_id
            demo_id += 1
        self._end_task()

    def _end_task(self, enable_sensor: bool = True) -> None:
        """
        End the task and update the frame data.

        :param enable_sensor: If True, enable the image sensor.
        """

        commands = [self._avatar.get_default_sticky_mitten_profile()]

        if enable_sensor:
            commands.append({"$type": "enable_image_sensor",
                             "enable": True,
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
        self.frame = FrameData(resp=resp, avatar=self._avatar)

    def communicate(self, commands: Union[dict, List[dict]]) -> List[bytes]:
        """
        Use this function to send low-level TDW API commands and receive low-level output data. See: [`Controller.communicate()`](https://github.com/threedworld-mit/tdw/blob/master/Documentation/python/controller.md)

        You shouldn't ever need to use this function, but you might see it in some of the example controllers because they might require a custom scene setup.

        :param commands: Commands to send to the build. See: [Command API](https://github.com/threedworld-mit/tdw/blob/master/Documentation/api/command_api.md).

        :return: The response from the build as a list of byte arrays. See: [Output Data](https://github.com/threedworld-mit/tdw/blob/master/Documentation/api/output_data.md).
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

        # Get the data.
        # There isn't any audio in this simulation, but we use `AudioInitData` anyway to derive physics values.
        init_data = AudioInitData(name=model_name, position=position, rotation=rotation, scale_factor=scale,
                                  audio=audio, library=library)
        object_id, commands = init_data.get_commands()
        if audio is None:
            audio = self._default_audio_values[model_name]
        self._audio_values[object_id] = audio

        return object_id, commands

    def reach_for_target(self, arm: Arm, target: Dict[str, float], check_if_possible: bool = True,
                         stop_on_mitten_collision: bool = True, precision: float = 0.05, absolute: bool = False) -> \
            TaskStatus:
        """
        Bend an arm joints of an avatar to reach for a target position.
        By default, the target is relative to the avatar's position and rotation.

        Possible [return values](task_status.md):

        - `success` (The avatar's arm's mitten reached the target position.)
        - `too_close_to_reach`
        - `too_far_to_reach`
        - `behind_avatar`
        - `no_longer_bending`
        - `mitten_collision` (If `stop_if_mitten_collision == True`)

        :param arm: The arm (left or right).
        :param target: The target position for the mitten.
        :param stop_on_mitten_collision: If true, the arm will stop bending if the mitten collides with an object other than the target object.
        :param check_if_possible: If True, before bending the arm, check if the mitten can reach the target assuming no obstructions; if not, don't try to bend the arm.
        :param precision: The precision of the action. If the mitten is this distance or less away from the target position, the action returns `success`.
        :param absolute: If True, `target` is in absolute world coordinates. If False, `target` is in coordinates relative to the avatar's position and rotation.

        :return: A `TaskStatus` indicating whether the avatar can reach the target and if not, why.
        """

        self._start_task()

        target = TDWUtils.vector3_to_array(target)

        # Convert to relative coordinates.
        if absolute:
            target = self._avatar.get_rotated_target(target=target)

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
        self._do_joint_motion()
        self._end_task()
        return self._get_avatar_status()

    def grasp_object(self, object_id: int, arm: Arm, check_if_possible: bool = True,
                     stop_on_mitten_collision: bool = True) -> TaskStatus:
        """
        The avatar's arm will reach for the object and continuously try to grasp the object.
        If it grasps the object, the simultation will attach the object to the avatar's mitten with an invisible joint. There may be some empty space between a mitten and a grasped object.
        This joint can be broken with sufficient force and torque.

        The grasped object's ID will be listed in [`FrameData.held_objects`](frame_data.md).

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
        :param arm: The arm of the mitten that will try to grasp the object.
        :param stop_on_mitten_collision: If true, the arm will stop bending if the mitten collides with an object.
        :param check_if_possible: If True, before bending the arm, check if the mitten can reach the target assuming no obstructions; if not, don't try to bend the arm.

        :return: A `TaskStatus` indicating whether the avatar picked up the object and if not, why.
        """

        if self._avatar.is_holding(object_id)[0]:
            return TaskStatus.success

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
        self._do_joint_motion()
        # The avatar failed to reach the target.
        if self._avatar.status != TaskStatus.success:
            self._end_task()
            return self._get_avatar_status()

        # Return whether the avatar picked up the object.
        self._avatar.status = TaskStatus.idle
        if self._avatar.is_holding(object_id=object_id)[0]:
            self._end_task()
            return TaskStatus.success
        else:
            self._end_task()
            return TaskStatus.failed_to_pick_up

    def drop(self, arm: Arm, reset_arm: bool = True) -> TaskStatus:
        """
        Drop any held objects held by the arm. Reset the arm to its neutral position.

        Possible [return values](task_status.md):

        - `success` (The avatar's arm dropped all objects held by the arm.)

        :param arm: The arm that will drop any held objects.
        :param reset_arm: If True, reset the arm's positions to "neutral".
        """

        self._start_task()

        self._avatar_commands.extend(self._avatar.drop(reset=reset_arm, arm=arm))
        self._do_joint_motion()
        self._end_task()
        return TaskStatus.success

    def reset_arm(self, arm: Arm) -> TaskStatus:
        """
        Reset an avatar's arm to its neutral positions.

        Possible [return values](task_status.md):

        - `success` (The arm reset to very close to its initial position.)
        - `no_longer_bending` (The arm stopped bending before it reset, possibly due to an obstacle in the way.)

        :param arm: The arm that will be reset.
        """

        self._start_task()

        self._avatar_commands.extend(self._avatar.reset_arm(arm=arm))
        self._do_joint_motion()
        self._end_task()
        return self._avatar.status

    def _do_joint_motion(self) -> None:
        """
        Step through the simulation until the joints of all avatars are done moving.
        """

        done = False
        step = 0
        while not done and step < 250:
            done = True
            step += 1
            # The loop is done if the IK goals are done.
            if not self._avatar.is_ik_done():
                done = False
            # Keep looping.
            if not done:
                self.communicate([])

    def _stop_avatar(self, enable_sensor: bool) -> None:
        """
        Stop the avatar's movement and turning.

        :param enable_sensor: If True, enable the image sensor.
        """

        self.communicate([{"$type": "set_avatar_drag",
                           "drag": self._STOP_DRAG,
                           "angular_drag": self._STOP_DRAG,
                           "avatar_id": self._avatar.id},
                          {"$type": "set_avatar_rigidbody_constraints",
                           "rotate": False,
                           "translate": False}])
        self._end_task(enable_sensor=enable_sensor)
        self._avatar.status = TaskStatus.idle

    def turn_to(self, target: Union[Dict[str, float], int], force: float = 1000,
                stopping_threshold: float = 0.15, num_attempts: int = 200,
                enable_sensor_on_finish: bool = True) -> TaskStatus:
        """
        Turn the avatar to face a target position or object.

        Possible [return values](task_status.md):

        - `success` (The avatar turned to face the target.)
        - `too_long` (The avatar made more attempts to turn than `num_attempts`.)

        :param target: Either the target position or the ID of the target object.
        :param force: The force at which the avatar will turn. More force = faster, but might overshoot the target.
        :param stopping_threshold: Stop when the avatar is within this many degrees of the target.
        :param num_attempts: The avatar will apply more angular force this many times to complete the turn before giving up.
        :param enable_sensor_on_finish: Enable the camera upon completing the task. This should only be set to False in the backend code.

        :return: A `TaskStatus` indicating whether the avatar turned successfully and if not, why.
        """

        def _get_turn_state() -> Tuple[TaskStatus, float]:
            """
            :return: Whether avatar succeed, failed, or is presently turning and the current angle.
            """

            angle = TDWUtils.get_angle(origin=np.array(self._avatar.frame.get_position()),
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
        initial_angle = TDWUtils.get_angle(origin=np.array(self._avatar.frame.get_position()),
                                           forward=np.array(self._avatar.frame.get_forward()),
                                           position=target)
        # Decide the shortest way to turn.
        if initial_angle > 0:
            direction = -1
        else:
            direction = 1

        self._avatar.status = TaskStatus.ongoing

        i = 0
        while i < num_attempts:
            self.communicate([{"$type": "set_avatar_rigidbody_constraints",
                               "rotate": True,
                               "translate": False},
                              {"$type": "set_avatar_drag",
                               "drag": 0,
                               "angular_drag": 0.05,
                               "avatar_id": self._avatar.id},
                              self._avatar.get_rotation_sticky_mitten_profile(),
                              {"$type": "turn_avatar_by",
                               "torque": force * direction,
                               "avatar_id": self._avatar.id}])
            # Coast to a stop.
            coasting = True
            while coasting:
                coasting = np.linalg.norm(self._avatar.frame.get_angular_velocity()) > 0.3
                state, previous_angle = _get_turn_state()
                # The turn succeeded!
                if state == TaskStatus.success:
                    self._stop_avatar(enable_sensor_on_finish)
                    return state
                # The turn failed.
                elif state != TaskStatus.ongoing:
                    self._stop_avatar(enable_sensor_on_finish)
                    return state
                self.communicate([])

            # Turn.
            state, previous_angle = _get_turn_state()
            # The turn succeeded!
            if state == TaskStatus.success:
                self._stop_avatar(enable_sensor_on_finish)
                return state
            # The turn failed.
            elif state != TaskStatus.ongoing:
                self._stop_avatar(enable_sensor_on_finish)
                return state
            i += 1
        self._stop_avatar(enable_sensor_on_finish)
        return TaskStatus.too_long

    def turn_by(self, angle: float, force: float = 1000, stopping_threshold: float = 0.15, num_attempts: int = 200) -> \
            TaskStatus:
        """
        Turn the avatar by an angle.

        Possible [return values](task_status.md):

        - `success` (The avatar turned by the angle.)
        - `too_long` (The avatar made more attempts to turn than `num_attempts`.)

        :param angle: The angle to turn to in degrees. If > 0, turn clockwise; if < 0, turn counterclockwise.
        :param force: The force at which the avatar will turn. More force = faster, but might overshoot the target.
        :param stopping_threshold: Stop when the avatar is within this many degrees of the target.
        :param num_attempts: The avatar will apply more angular force this many times to complete the turn before giving up.

        :return: A `TaskStatus` indicating whether the avatar turned successfully and if not, why.
        """

        # Rotate the forward directional vector.
        p0 = self._avatar.frame.get_forward()
        p1 = TDWUtils.rotate_position_around(origin=np.array([0, 0, 0]), position=p0, angle=angle)
        # Get a point to look at.
        p1 = np.array(self._avatar.frame.get_position()) + (p1 * 1000)
        return self.turn_to(target=TDWUtils.array_to_vector3(p1), force=force, stopping_threshold=stopping_threshold,
                            num_attempts=num_attempts)

    def go_to(self, target: Union[Dict[str, float], int], turn_force: float = 1000, move_force: float = 80,
              turn_stopping_threshold: float = 0.15, move_stopping_threshold: float = 0.35,
              stop_on_collision: bool = True, turn: bool = True, num_attempts: int = 200) -> TaskStatus:
        """
        Move the avatar to a target position or object.

        Possible [return values](task_status.md):

        - `success` (The avatar arrived at the target.)
        - `too_long` (The avatar made more attempts to move or to turn than `num_attempts`.)
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
        :param num_attempts: The avatar will apply more force this many times to complete the turn before giving up.

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
                if self._avatar.base_id in self._avatar.env_collisions:
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

        initial_position = self._avatar.frame.get_position()

        # Get the distance to the target.
        initial_distance = np.linalg.norm(np.array(initial_position) - target)

        if turn:
            # Turn to the target.
            status = self.turn_to(target=TDWUtils.array_to_vector3(target), force=turn_force,
                                  stopping_threshold=turn_stopping_threshold, num_attempts=num_attempts,
                                  enable_sensor_on_finish=False)
            if status != TaskStatus.success:
                self._stop_avatar(True)
                return status
        self._start_task()
        self._avatar.status = TaskStatus.ongoing
        i = 0
        while i < num_attempts:
            # Start gliding.
            self.communicate([{"$type": "set_avatar_rigidbody_constraints",
                               "rotate": False,
                               "translate": True},
                              {"$type": "move_avatar_forward_by",
                               "magnitude": move_force,
                               "avatar_id": self._avatar.id},
                              {"$type": "set_avatar_drag",
                               "drag": 0.1,
                               "angular_drag": 100,
                               "avatar_id": self._avatar.id},
                              self._avatar.get_movement_sticky_mitten_profile()])
            t = _get_state()
            if t == TaskStatus.success:
                self._stop_avatar(True)
                return t
            elif t != TaskStatus.ongoing:
                self._stop_avatar(True)
                return t
            # Glide.
            while np.linalg.norm(self._avatar.frame.get_velocity()) > 0.1:
                self.communicate([])
                t = _get_state()
                if t == TaskStatus.success:
                    self._stop_avatar(True)
                    return t
                elif t != TaskStatus.ongoing:
                    self._stop_avatar(True)
                    return t
            i += 1
        self._stop_avatar(True)
        return TaskStatus.too_long

    def move_forward_by(self, distance: float, move_force: float = 80, move_stopping_threshold: float = 0.35,
                        stop_on_collision: bool = True, num_attempts: int = 200) -> TaskStatus:
        """
        Move the avatar forward by a distance along the avatar's current forward directional vector.

        Possible [return values](task_status.md):

        - `success` (The avatar moved forward by the distance.)
        - `too_long` (The avatar made more attempts to move than `num_attempts`.)
        - `overshot`
        - `collided_with_something_heavy` (if `stop_on_collision == True`)
        - `collided_with_environment` (if `stop_on_collision == True`)

        :param distance: The distance that the avatar will travel. If < 0, the avatar will move backwards.
        :param move_force: The force at which the avatar will move. More force = faster, but might overshoot the target.
        :param move_stopping_threshold: Stop within this distance of the target.
        :param stop_on_collision: If True, stop moving when the object collides with a large object (mass > 90) or the environment (e.g. a wall).
        :param num_attempts: The avatar will apply more force this many times to complete the turn before giving up.

        :return: A `TaskStatus` indicating whether the avatar moved forward by the distance and if not, why.
        """

        # The target is at `distance` away from the avatar's position along the avatar's forward directional vector.
        target = np.array(self._avatar.frame.get_position()) + (np.array(self._avatar.frame.get_forward()) * distance)
        return self.go_to(target=target, move_force=move_force, move_stopping_threshold=move_stopping_threshold,
                          stop_on_collision=stop_on_collision, turn=False, num_attempts=num_attempts)
    
    def put_in_container_for_model_training(self) -> TaskStatus: 
        self._start_task() 
        container_id: Optional[int] = None 
        for arm in self.frame.held_objects: 
            for o_id in self.frame.held_objects[arm]: 
                if self.static_object_info[o_id].container: 
                    container_id = o_id 
        if container_id is None: 
            return TaskStatus.not_a_container 
        self.container_masses[container_id] += TARGET_OBJECT_MASS 
        self._avatar_commands.append({"$type": "set_mass", 
                                      "id": container_id, 
                                      "mass": self.container_masses[container_id]}) 
        self._end_task() 
        return TaskStatus.success 
    
    def put_in_container(self, object_id: int, container_id: int, arm: Arm) -> TaskStatus:
        """
        Try to put an object in a container.

        1. The avatar will grasp the object and a container via `grasp_object()` if it isn't holding them already.
        2. The avatar will lift the object up.
        3. The container and its contents will be teleported to be in front of the avatar.
        4. The avatar will move the object over the container and drop it.
        5. The avatar will pick up the container again.

        Once an object is placed in a container, _it can not be removed again_.
        The object will be permanently attached to the container.

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
        - `full_container`

        :param object_id: The ID of the object that the avatar will try to put in the container.
        :param container_id: The ID of the container. To determine if an object is a container, see [`StaticObjectInfo.container`](static_object_info.md).
        :param arm: The arm that will try to pick up the object.

        :return: A `TaskStatus` indicating whether the avatar put the object in the container and if not, why.
        """

        if not self.static_object_info[container_id].container:
            return TaskStatus.not_a_container

        container_id = int(container_id)

        self._stop_avatar(enable_sensor=False)

        # A "full" container has too many objects such that physics might glitch.
        overlap_ids = self._get_objects_in_container(container_id=container_id)
        '''if len(overlap_ids) > 3:
            self._end_task()
            return TaskStatus.full_container'''

        # Grasp the object.
        if object_id not in self.frame.held_objects[arm]:
            status = self.grasp_object(object_id=object_id, arm=arm)
            if status != TaskStatus.success:
                self._end_task(enable_sensor=False)
                return status
        container_arm = Arm.left if arm == Arm.right else Arm.right

        # Lift up the object.
        self.reach_for_target(target={"x": 0.35 if arm == Arm.right else -0.35, "y": 0.3, "z": 0.36},
                              arm=arm,
                              check_if_possible=False,
                              stop_on_mitten_collision=False,
                              precision=0.2)

        # Let the container fall to the ground.
        self.drop(arm=container_arm)
        self.reset_arm(arm=container_arm)

        # Try to nudge the container to be directly in front of the avatar.
        new_container_position = self.frame.avatar_transform.position + np.array([-0.215 if arm == Arm.right else 0.215,
                                                                                  0, 0.341])
        new_container_angle = TDWUtils.get_angle(forward=self.frame.avatar_transform.forward,
                                                 origin=self.frame.avatar_transform.position,
                                                 position=new_container_position)
        new_container_position = TDWUtils.rotate_position_around(position=new_container_position,
                                                                 origin=self.frame.avatar_transform.position,
                                                                 angle=new_container_angle)

        self.communicate([{"$type": "rotate_object_to",
                           "rotation": TDWUtils.array_to_vector4(self.frame.avatar_transform.rotation),
                           "id": container_id,
                           "physics": True},
                          {"$type": "teleport_object",
                           "position": TDWUtils.array_to_vector3(new_container_position),
                           "id": container_id,
                           "physics": True},
                          {"$type": "set_avatar_rigidbody_constraints",
                           "rotate": False,
                           "translate": False}])

        self._wait_for_objects_to_stop(object_ids=[container_id])
        self._end_task()

        # Lift the arm away.
        self.reach_for_target(target={"x": 0.25 if arm == Arm.right else -0.25, "y": 0.6, "z": 0.3},
                              arm=arm,
                              check_if_possible=False,
                              stop_on_mitten_collision=False)
        aim_position = self.frame.object_transforms[container_id].position
        aim_position[1] = 0.3
        self.reach_for_target(arm=arm,
                              target={"x": 0, "y": 0.306, "z": 0.392},
                              stop_on_mitten_collision=False,
                              check_if_possible=False)

        self._end_task(enable_sensor=False)

        # Drop the object.
        self.drop(arm=arm, reset_arm=False)

        # Lift the arm away.
        self.reach_for_target(target={"x": 0.25 if arm == Arm.right else -0.25, "y": 0.6, "z": 0.3},
                              arm=arm,
                              check_if_possible=False,
                              stop_on_mitten_collision=False)

        self.reset_arm(arm=arm)
        self._wait_for_objects_to_stop(object_ids=[object_id])

        if object_id not in self._get_objects_in_container(container_id=container_id):
            print(self._get_objects_in_container(container_id=container_id))
            return TaskStatus.not_in_container

        # Connect the object to the container.
        '''self.communicate({"$type": "add_fixed_joint",
                          "id": object_id,
                          "parent_id": container_id})'''
        position = {'x': float(20 + random.randint(0, 10)), 
                    'y': float(0.),
                    'z': float(20 + random.randint(0, 10))}
            
        self.communicate([{"$type": "teleport_object",
               "position": position,
               "id": object_id,
               "physics": True}])
        self.reset_arm(arm=container_arm)

        # Move the container and its objects in front of the mitten.
        mitten_id = self._avatar.mitten_ids[container_arm]
        new_container_position = self.frame.avatar_body_part_transforms[mitten_id].position + self.frame.\
            avatar_transform.forward * 0.3
        delta_position = new_container_position - self.frame.object_transforms[container_id].position
        teleport_commands = [{"$type": "teleport_object",
                              "id": container_id,
                              "position": TDWUtils.array_to_vector3(new_container_position),
                              "physics": True}]
        for overlap_id in overlap_ids:
            if overlap_id not in self.frame.object_transforms:
                continue
            teleport_position = self.frame.object_transforms[overlap_id].position + delta_position
            teleport_position[1] += 0.03
            teleport_commands.append({"$type": "teleport_object",
                                      "id": overlap_id,
                                      "position": TDWUtils.array_to_vector3(teleport_position),
                                      "physics": True})

        self.communicate(teleport_commands)

        self._wait_for_objects_to_stop(object_ids=[object_id])

        # Pick up the container again.
        return self.grasp_object(object_id=container_id, arm=container_arm, check_if_possible=False)

    def rotate_camera_by(self, pitch: float = 0, yaw: float = 0) -> None:
        """
        Rotate an avatar's camera. The head of the avatar won't visually rotate because it would cause the entire avatar to tilt.

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
        self._avatar_commands.extend(commands)
        self._end_task()

    def reset_camera_rotation(self) -> None:
        """
        Reset the rotation of the avatar's camera.
        """

        self._start_task()

        self._avatar_commands.append({"$type": "reset_sensor_container_rotation",
                                      "avatar_id": self._avatar.id})
        self._end_task()

    def add_overhead_camera(self, position: Dict[str, float], target_object: Union[str, int] = None, cam_id: str = "c",
                            images: str = "all") -> None:
        """
        Add an overhead third-person camera to the scene. This is meant only for demo or debugging purposes, _not_ for gathering multiple image passes.

        :param cam_id: The ID of the camera.
        :param target_object: Always point the camera at this object or avatar.
        :param position: The position of the camera.
        :param images: Image capture behavior. Choices: `"cam"` (only this camera captures images); `"all"` (avatars currently in the scene and this camera capture images); `"avatars"` (only the avatars currently in the scene capture images)
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
        '''self._cam_commands.append({"$type": "enable_image_sensor",
                                   "enable": False,
                                   "sensor_name": "SensorContainer",
                                   "avatar_id": self._avatar.id})'''
        if images != "avatars":
            commands.append({"$type": "set_pass_masks",
                             "pass_masks": ["_img"],
                             "avatar_id": cam_id})
        if images == "cam":
            # Disable avatar cameras.
            commands.append({"$type": "enable_image_sensor",
                             "enable": False,
                             "sensor_name": "SensorContainer",
                             "avatar_id": self._avatar.id})

            commands.append({"$type": "send_images",
                             "ids": [cam_id],
                             "frequency": "always"})
        elif images == "all":
            commands.append({"$type": "send_images",
                             "frequency": "always"})
        self._avatar_commands.extend(commands)
        self._end_task()

    def _get_objects_in_container(self, container_id: int) -> np.array:
        """
        :param container_id: The ID of the container.

        :return: A numpy array of the IDs of all objects in the container.
        """

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

        up = QuaternionUtils.get_up_direction(rot)

        # Get the shape of the container.
        name = self.static_object_info[container_id].model_name
        shape = self._container_shapes[name]

        # Check the overlap of the container to see if the object is in that space. If so, it is in the container.
        size = self.static_object_info[container_id].size
        # Set the position to be in the center of the rotated object.
        center = TDWUtils.array_to_vector3(pos + (up * size[1] * 0.5))
        pos = TDWUtils.array_to_vector3(pos)
        # Decide which overlap shape to use depending on the container shape.
        if shape == "box":
            resp = self.communicate({"$type": "send_overlap_box",
                                     "position": pos,
                                     "rotation": TDWUtils.array_to_vector4(rot),
                                     "half_extents": TDWUtils.array_to_vector3(size)})
        elif shape == "sphere":
            resp = self.communicate({"$type": "send_overlap_sphere",
                                     "position": pos,
                                     "radius": min(size)})
        elif shape == "capsule":
            resp = self.communicate({"$type": "send_overlap_capsule",
                                     "position": pos,
                                     "end": center,
                                     "radius": min(size)})
        else:
            raise Exception(f"Bad shape for {name}: {shape}")
        overlap = get_data(resp=resp, d_type=Overlap)
        return [int(o_id) for o_id in overlap.get_object_ids() if int(o_id) != container_id]

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

    def end(self) -> None:
        """
        End the simulation. Terminate the build process.
        """

        self.communicate({"$type": "terminate"})

    def get_occupancy_position(self, i: int, j: int) -> Tuple[float, float]:
        """
        Converts the position (i, j) in the occupancy map to (x, z) coordinates.

        :param i: The i coordinate in the occupancy map.
        :param j: The j coordinate in the occupancy map.

        :return: Tuple: x coordinate; z coordinate.
        """

        if self.occupancy_map is None or self._scene_bounds is None:
            raise Exception(f"Position {i}, {j} is not on the occupancy map.")
        x = self._scene_bounds["x_min"] + (i * OCCUPANCY_CELL_SIZE)
        z = self._scene_bounds["z_min"] + (j * OCCUPANCY_CELL_SIZE)
        return x, z

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

    def _roll_wrist(self, arm: Arm, angle: float, precision: float = 0.02) -> None:
        """
        Roll the wrist to a target angle.

        :param arm: The arm.
        :param angle: The target angle.
        :param precision: Precision of the movement (the threshold at which the angle is considered equal).
        """

        # Begin rotation.
        self.communicate([self._avatar.get_roll_wrist_sticky_mitten_profile(arm=arm),
                          {"$type": "bend_arm_joint_to",
                           "angle": angle,
                           "joint": f"wrist_{arm.name}",
                           "axis": "roll",
                           "avatar_id": self._avatar.id}])
        # Wait for the motion to finish.
        a0 = self._avatar.frame.get_angles_left()[-2] if arm == Arm.left else \
            self._avatar.frame.get_angles_right()[-2]
        done_twisting_wrist = False
        while not done_twisting_wrist:
            self.communicate([])
            # Get the angle of the wrist.
            a1 = self._avatar.frame.get_angles_left()[-2] if arm == Arm.left else \
                self._avatar.frame.get_angles_right()[-2]
            done_twisting_wrist = np.abs(a1 - a0) < precision
            a0 = a1

    def _get_scene_init_commands(self, scene: str = None, layout: int = None, room: int = -1) -> List[dict]:
        """
        Get commands to initialize the scene before adding avatars.

        :param scene: The name of the scene. Can be None.
        :param layout: The layout index. Can be None.
        :param room: The room number. If -1, the room is chosen randomly.

        :return: A list of commands to initialize the scene. Override this function for a different "scene recipe".
        """

        if scene is None or layout is None:
            commands = [{"$type": "load_scene",
                         "scene_name": "ProcGenScene"},
                        TDWUtils.create_empty_room(12, 12)]
            avatar_position = TDWUtils.VECTOR3_ZERO
        else:
            commands = self.get_scene_init_commands(scene=scene, layout=layout, audio=True)

            self._scene_bounds = loads(SCENE_BOUNDS_PATH.read_text())[scene[0]]
            room_map = np.load(str(ROOM_MAP_DIRECTORY.joinpath(f"{scene[0]}.npy").resolve()))
            map_filename = f"{scene[0]}_{layout}.npy"
            self.occupancy_map = np.load(
                str(OCCUPANCY_MAP_DIRECTORY.joinpath(map_filename).resolve()))
            ys_map = np.load(str(Y_MAP_DIRECTORY.joinpath(map_filename).resolve()))
            object_spawn_map = np.load(str(OBJECT_SPAWN_MAP_DIRECTORY.joinpath(map_filename).resolve()))

            #add container
            for c in self.data['container']:
                ix, iy = c['ixy']
                x, z = self.get_occupancy_position(ix, iy)
                container_name = c['name']
                SCALE = {"x": 0.5, "y": 0.4, "z": 0.5}
                #SCALE = CONTAINER_SCALE
                container_id, container_commands = self._add_object(position=c['position'],
                                                                    rotation=c['rotation'],
                                                                    scale=SCALE,
                                                                    audio=self._default_audio_values[
                                                                        container_name],
                                                                    model_name=container_name)
                commands.extend(container_commands)
                # Make the container much lighter.
                commands.append({"$type": "set_mass",
                                 "id": container_id,
                                 "mass": CONTAINER_MASS})
                self.container_masses[container_id] = CONTAINER_MASS
                # Mark this space as occupied.
                self.occupancy_map[ix][iy] = 0
            
            #add target objects
            for o in self.data['target_object']:
                ix, iy = o['ixy']
                x, z = self.get_occupancy_position(ix, iy)
                target_object_name = o['name']
                audio = ObjectInfo(name=target_object_name, mass=TARGET_OBJECT_MASS, material=AudioMaterial.ceramic,
                                   resonance=0.6, amp=0.01, library="models_core.json", bounciness=0.5)
                scale = o['scale']
                object_id, object_commands = self._add_object(position=o['position'],
                                                              rotation=o['rotation'],
                                                              scale={"x": scale, "y": scale, "z": scale},
                                                              audio=audio,
                                                              model_name=target_object_name)
                self._target_object_ids.append(object_id)
                commands.extend(object_commands)
                
                # Set a random visual material for each target object.
                visual_material = o['visual_material']
                substructure = AudioInitData.LIBRARIES["models_core.json"].get_record(target_object_name). \
                    substructure
                commands.extend(TDWUtils.set_visual_material(substructure=substructure,
                                                             material=visual_material,
                                                             object_id=object_id,
                                                             c=self))

                # Mark this space as occupied.
                self.occupancy_map[ix][iy] = 0
            
            #goal
            # Set the goal positions and goal_object.
            goal_positions = loads(SURFACE_MAP_DIRECTORY.joinpath(f"{scene[0]}_{layout}.json").
                                   read_text(encoding="utf-8"))
            self.goal_positions = dict()
            for k in goal_positions:
                self.goal_positions[int(k)] = goal_positions[k]
                
            self.goal_object = self.data['goal_object']
            
            #positon
            avatar_position = self.data['avatar_position']
            

        # Create the avatar.
        commands.extend(TDWUtils.create_avatar(avatar_type="A_StickyMitten_Baby", avatar_id="a"))

        if self._id_pass:
            pass_masks = ["_img", "_id", "_depth"]
        else:
            pass_masks = ["_img", "_depth"]

        # Request segmentation colors, body part names, and dynamic avatar data.
        # Turn off the follow camera.
        # Set the palms to sticky.
        # Enable image capture.
        # Teleport the avatar to its initial position.
        # Set the initial joint values.
        commands.extend([{"$type": "send_avatar_segmentation_colors"},
                         {"$type": "send_avatars",
                          "frequency": "always"},
                         {"$type": "set_avatar_drag",
                          "drag": self._STOP_DRAG,
                          "angular_drag": self._STOP_DRAG},
                         {"$type": "set_pass_masks",
                          "pass_masks": pass_masks},
                         {"$type": "enable_image_sensor",
                          "enable": False,
                          "sensor_name": "FollowCamera"},
                         {"$type": "teleport_avatar_to",
                          "avatar_id": "a",
                          "position": avatar_position}])
        
        # Set all sides of both mittens to be sticky.
        for sub_mitten in ["palm", "back", "side"]:
            for is_left in [True, False]:
                commands.append({"$type": "set_stickiness",
                                 "sub_mitten": sub_mitten,
                                 "sticky": True,
                                 "is_left": is_left,
                                 "show": False})

        # Request initial output data.
        commands.extend([{"$type": "send_collisions",
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
                          "frequency": "once"}])

        return commands

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

        self._avatar_commands.append({"$type": "enable_image_sensor",
                                      "enable": False,
                                      "sensor_name": "SensorContainer",
                                      "avatar_id": self._avatar.id})

    def _wait_for_objects_to_stop(self, object_ids: List[int]) -> None:
        """
        Wait for some objects to stop moving.

        :param object_ids: A list of object IDs.
        """

        # Request rigidbody data per frame for each of the objects.
        resp = self.communicate([{"$type": "send_rigidbodies",
                                  "frequency": "always",
                                  "ids": object_ids},
                                 {"$type": "send_transforms",
                                  "frequency": "always",
                                  "ids": object_ids}])
        sleeping = False
        # Set a maximum number of frames to prevent an infinite loop.
        num_frames = 0
        while not sleeping and num_frames < 200:
            sleeping = True
            # Advance one frame.
            rigidbodies = get_data(resp=resp, d_type=Rigidbodies)
            # Get all objects below the floor.
            transforms = get_data(resp=resp, d_type=Transforms)
            below_floor: List[int] = list()
            for i in range(transforms.get_num()):
                if transforms.get_position(i)[1] < -1:
                    below_floor.append(transforms.get_id(i))

            # Check if the object stopped moving.
            for i in range(rigidbodies.get_num()):
                # Ignore objects that are perpectually falling.
                if rigidbodies.get_id(i) in below_floor:
                    continue
                # Check if this object is moving.
                if np.linalg.norm(rigidbodies.get_velocity(i)) > 0.1:
                    sleeping = False
                    break
            resp = self.communicate([])
            num_frames += 1

        self._end_task(enable_sensor=False)
