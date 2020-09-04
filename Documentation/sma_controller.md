# `sticky_mitten_avatar/sma_controller.py`

## `StickyMittenAvatarController(Controller)`

`from tdw.sticky_mitten_avatar.sma_controller import StickyMittenAvatarController`

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

- `frame` Dynamic data for the current frame. Overwrites itself per frame.
               [Read this](frame_data.md) for a full API.
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

- `on_resp` Default = None. Set this to a function with a `resp` argument to do something per-frame:

```python
def _per_frame():
    print("This will happen every frame.")

c.on_resp = _per_frame
```

***

#### `__init__(self, port: int = 1071, launch_build: bool = True, audio_playback_mode: str = None)`


| Parameter | Description |
| --- | --- |
| port | The port number. |
| launch_build | If True, automatically launch the build. |
| audio_playback_mode | How the build will play back audio. Options: None (no playback, but audio will be generated in `self.frame_data`), `"unity"` (use the standard Unity audio system), `"resonance_audio"` (use Resonance Audio). |

***

#### `init_scene(self) -> None`

Initialize a scene, populate it with objects,
add the avatar, and set rendering options such as post-processing values.
Then, request relevant output data per frame (collisions, transforms, etc.),
initialize image capture, and cache [static object data](static_object_data.md).
Each subclass of StickyMittenAvatarController has a specialized "recipe" for `init_scene()`.

***

#### `create_avatar(self, avatar_type: str = "baby", avatar_id: str = "a", position: Dict[str, float] = None, rotation: float = 0, debug: bool = False) -> None`

Create an avatar. Set default values for the avatar. Cache its static data (segmentation colors, etc.)

| Parameter | Description |
| --- | --- |
| avatar_type | The type of avatar. Options: "baby", "adult" |
| avatar_id | The unique ID of the avatar. |
| position | The initial position of the avatar. |
| rotation | The initial rotation of the avatar in degrees. |
| debug | If true, print debug messages when the avatar moves. |

***

#### `communicate(self, commands: Union[dict, List[dict]]) -> List[bytes]`

Overrides `Controller.communicate()`.
Before sending commands, append any automatically-added commands (such as arm-bending or arm-stopping).
If there is a third-person camera, append commands to look at a target (see `add_overhead_camera()`).
After sending the commands, update the avatar's `frame` data, and dynamic object data.
Then, invoke `self.on_resp()` if it is not None.

| Parameter | Description |
| --- | --- |
| commands | Commands to send to the build. |

_Returns:_  The response from the build.

***

#### `get_add_object(self, model_name: str, object_id: int, position: Dict[str, float] = None, rotation: Dict[str, float] = None, library: str = "", scale: Dict[str, float] = None, audio: ObjectInfo = None) -> List[dict]`

Overrides Controller.get_add_object; returns a list of commands instead of 1 command.
See `ModelLibrarian.get_library_filenames()` and `ModelLibrarian.get_default_library()`.

| Parameter | Description |
| --- | --- |
| model_name | The name of the model. |
| position | The position of the model. |
| rotation | The starting rotation of the model, in Euler angles. |
| library | The path to the records file. If left empty, the default library will be selected. |
| object_id | The ID of the new object. |
| scale | The scale factor of the object. If None, the scale factor is (1, 1, 1) |
| audio | Audio values for the object. If None, use default values. |

_Returns:_  A list of commands: `[add_object, set_mass, scale_object ,set_object_collision_detection_mode, set_physic_material]`

***

#### `get_container_records(self) -> List[ModelRecord]`

_Returns:_  A list of container [model records](https://github.com/threedworld-mit/tdw/blob/master/Documentation/python/librarian/model_librarian.md#modelrecord-api).

***

#### `get_add_container(self, model_name: str, object_id: int, contents: List[str], position: Dict[str, float] = None, rotation: Dict[str, float] = None, audio: ObjectInfo = None, scale: Dict[str, float] = None) -> List[dict]`

Add a container to the scene. A container is an object that can hold other objects in it.
Containers must be from the "containers" library. See `get_container_records()`.

| Parameter | Description |
| --- | --- |
| model_name | The name of the container. |
| object_id | The ID of the container. |
| contents | The model names of objects that will be put in the container. They will be assigned random positions and object IDs and default audio and physics values. |
| position | The position of the container. |
| rotation | The rotation of the container. |
| audio | Audio values for the container. If None, use default values. |
| scale | The scale of the container. |

_Returns:_  A list of commands per object added: `[add_object, set_mass, scale_object ,set_object_collision_detection_mode, set_physic_material]`

***

#### `bend_arm(self, avatar_id: str, arm: Arm, target: Dict[str, float], do_motion: bool = True) -> bool`

Begin to bend an arm of an avatar in the scene. The motion will continue to update per `communicate()` step.

| Parameter | Description |
| --- | --- |
| arm | The arm (left or right). |
| target | The target position for the mitten. |
| avatar_id | The unique ID of the avatar. |
| do_motion | If True, advance simulation frames until the pick-up motion is done. See: `do_joint_motion()` |

_Returns:_  True if the avatar bends the arm.

***

#### `pick_up(self, avatar_id: str, object_id: int, do_motion: bool = True) -> Arm`

Begin to bend an avatar's arm to try to pick up an object in the scene.
The simulation will advance 1 frame (to collect the object's bounds data).
The motion will continue to update per `communicate()` step.

| Parameter | Description |
| --- | --- |
| object_id | The ID of the target object. |
| avatar_id | The unique ID of the avatar. |
| do_motion | If True, advance simulation frames until the pick-up motion is done. See: `do_joint_motion()` |

_Returns:_  The arm that is picking up the object.

***

#### `put_down(self, avatar_id: str, reset_arms: bool = True, do_motion: bool = True) -> None`

Begin to put down all objects.
The motion will continue to update per `communicate()` step.

| Parameter | Description |
| --- | --- |
| avatar_id | The unique ID of the avatar. |
| reset_arms | If True, reset arm positions to "neutral". |
| do_motion | If True, advance simulation frames until the pick-up motion is done. See: `do_joint_motion()` |

***

#### `reset_arms(self, avatar_id: str, do_motion: bool = True) -> None`

Reset the avatar's arm joints to their starting positions.

| Parameter | Description |
| --- | --- |
| avatar_id | The ID of the avatar. |
| do_motion | If True, advance simulation frames until the pick-up motion is done. See: `do_joint_motion()` |

***

#### `do_joint_motion(self) -> None`

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

***

#### `stop_avatar(self, avatar_id: str) -> None`

Advance 1 frame and stop the avatar's movement and turning.

| Parameter | Description |
| --- | --- |
| avatar_id | The ID of the avatar. |

***

#### `turn_to(self, avatar_id: str, target: Union[Dict[str, float], int], force: float = 1000, stopping_threshold: float = 0.15) -> bool`

The avatar will turn to face a target. This will advance through many simulation frames.

| Parameter | Description |
| --- | --- |
| avatar_id | The unique ID of the avatar. |
| target | The target position or object ID. |
| force | The force at which the avatar will turn. More force = faster, but might overshoot the target. |
| stopping_threshold | Stop when the avatar is within this many degrees of the target. |

_Returns:_  True if the avatar succeeded in turning to face the target.

***

#### `get_turn_state() -> _TaskState`

_Returns:_  Whether avatar succeed, failed, or is presently turning.

***

#### `go_to(self, avatar_id: str, target: Union[Dict[str, float], int], turn_force: float = 1000, turn_stopping_threshold: float = 0.15, move_force: float = 80, move_stopping_threshold: float = 0.35) -> bool`

Go to a target position or object.
If the avatar isn't facing the target, it will turn to face it (see `turn_to()`).
The task will end in success if the avatar reaches the destination.
The task will end in failure if:
- The avatar overshot the target.
- The avatar's body collided with a heavy object (mass >= 90)
- The avatar collided with part of the environment (such as a wall).

| Parameter | Description |
| --- | --- |
| avatar_id | The unique ID of the avatar. |
| target | The target position or object ID. |
| turn_force | The force at which the avatar will turn. More force = faster, but might overshoot the target. |
| turn_stopping_threshold | Stop when the avatar is within this many degrees of the target. |
| move_force | The force at which the avatar will move. More force = faster, but might overshoot the target. |
| move_stopping_threshold | Stop within this distance of the target. |

_Returns:_  True if the avatar arrived at the destination.

***

#### `get_state() -> _TaskState`

_Returns:_  Whether the avatar is at its destination, overshot it, or still going to it.

***

#### `shake(self, avatar_id: str, joint_name: str = "elbow_left", axis: str = "pitch", angle: Tuple[float, float] = (20, 30), num_shakes: Tuple[int, int] = (3, 5), force: Tuple[float, float] = (900, 1000)) -> None`

Shake a joint back and forth for multiple iterations.
Per iteration, the joint will bend forward by an angle and then bend back by an angle.
This will advance the simulation multiple frames.

| Parameter | Description |
| --- | --- |
| avatar_id | The ID of the avatar. |
| joint_name | The name of the joint. |
| axis | The axis of the joint's rotation. |
| angle | Each shake will bend the joint by a angle in degrees within this range. |
| num_shakes | The avatar will shake the joint a number of times within this range. |
| force | The avatar will add strength to the joint by a value within this range. |

***

#### `add_overhead_camera(self, position: Dict[str, float], target_object: Union[str, int] = None, cam_id: str = "c", images: str = "all") -> None`

Add an overhead third-person camera to the scene.
Advances 1 frame.
1. `"cam"` (only this camera captures images)
2. `"all"` (avatars currently in the scene and this camera capture images)
3. `"avatars"` (only the avatars currently in the scene capture images)

| Parameter | Description |
| --- | --- |
| cam_id | The ID of the camera. |
| target_object | Always point the camera at this object or avatar. |
| position | The position of the camera. |
| images | Image capture behavior. Choices: |

***

#### `destroy_avatar(self, avatar_id: str) -> None`

Destroy an avatar or camera in the scene.

| Parameter | Description |
| --- | --- |
| avatar_id | The ID of the avatar or camera. |

***

#### `end(self) -> None`

End the simulation. Terminate the build process.

***

#### `_get_scene_init_commands_early(self) -> List[dict]`

Get commands to initialize the scene before adding avatars.

_Returns:_  A list of commands to initialize the scene. Override this function for a different "scene recipe".

***

#### `_do_scene_init_late(self) -> None`

Initialize the scene after adding avatars.

***

#### `_init_avatar(self) -> None`

Initialize the avatar.

***

