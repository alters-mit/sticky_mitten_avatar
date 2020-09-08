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
avatar_id = c.init_scene()

# Bend an arm.
c.bend_arm(target={"x": -0.2, "y": 0.21, "z": 0.385}, arm=Arm.left)

# Get the segementation color pass for the avatar after bending the arm.
segmentation_colors = c.frame.images[avatar_id][0]
```

***

Fields:

- `frame` Dynamic data for the current frame, updated per frame. [Read this](frame_data.md) for a full API.
  Note: Most of the avatar API advances the simulation multiple frames. `frame` is current to frame at the end of an action.
```python
# Get the segementation color pass for the avatar after bending the arm.
segmentation_colors = c.frame.images[avatar_id][0]
```

- `static_object_data`: Static info for all objects in the scene. [Read this](static_object_info.md) for a full API.

```python
# Get the segmentation color of an object.
segmentation_color = c.static_object_info[object_id].segmentation_color
```

- `static_avatar_data` Static info for the body parts of each avatar in the scene. [Read this](body_part_static.md) for a full API.


```python
for avatar_id in c.static_avatar_data.avatars:
    for body_part_id in c.static_avatar_data.avatars[avatar_id]:
        body_part = c.static_avatar_data.avatars[avatar_id][body_part_id]
        print(body_part.object_id) # The object ID of the body part (matches body_part_id).
        print(body_part.color) # The segmentation color.
        print(body_part.name) # The name of the body part.
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

Initialize a scene, populate it with objects, add the avatar, and set rendering options.
Then, request data per frame (collisions, transforms, etc.), initialize image capture, and cache static data.
Each subclass of `StickyMittenAvatarController` overrides this function to have a specialized scene setup.

***

#### `communicate(self, commands: Union[dict, List[dict]]) -> List[bytes]`

Overrides [`Controller.communicate()`](https://github.com/threedworld-mit/tdw/blob/master/Documentation/python/controller.md).
Before sending commands, append any automatically-added commands (such as arm-bending or arm-stopping).
If there is a third-person camera, append commands to look at a target (see `add_overhead_camera()`).
After receiving a response from the build, update the `frame` data.

| Parameter | Description |
| --- | --- |
| commands | Commands to send to the build. |

_Returns:_  The response from the build.

***

#### `bend_arm(self, arm: Arm, target: Dict[str, float], do_motion: bool = True, avatar_id: str = "a") -> bool`

Bend an arm of an avatar until the mitten is at the target position.
If the position is sufficiently out of reach, the arm won't bend.
Otherwise, the motion continues until the mitten is either at the target position or the arm stops moving.

| Parameter | Description |
| --- | --- |
| arm | The arm (left or right). |
| target | The target position for the mitten relative to the avatar. |
| avatar_id | The unique ID of the avatar. |
| do_motion | If True, advance simulation frames until the pick-up motion is done. |

_Returns:_  True if the mitten is near the target position.

***

#### `pick_up(self, object_id: int, do_motion: bool = True, avatar_id: str = "a") -> (bool, Arm)`

Bend the arm of an avatar towards an object. Per frame, try to pick up the object.
If the position is sufficiently out of reach, the arm won't bend.
The motion continues until either the object is picked up or the arm stops moving.

| Parameter | Description |
| --- | --- |
| object_id | The ID of the target object. |
| avatar_id | The unique ID of the avatar. |
| do_motion | If True, advance simulation frames until the pick-up motion is done. |

_Returns:_  Tuple: True if the avatar picked up the object, and the arm that is picking up the object.

***

#### `put_down(self, reset_arms: bool = True, do_motion: bool = True, avatar_id: str = "a") -> None`

Begin to put down all objects.
The motion continues until the arms have reset to their neutral positions.

| Parameter | Description |
| --- | --- |
| avatar_id | The unique ID of the avatar. |
| reset_arms | If True, reset arm positions to "neutral". |
| do_motion | If True, advance simulation frames until the pick-up motion is done. |

***

#### `reset_arms(self, do_motion: bool = True, avatar_id: str = "a") -> None`

Reset the avatar's arm joint positions.
The motion continues until the arms have reset to their neutral positions.

| Parameter | Description |
| --- | --- |
| avatar_id | The ID of the avatar. |
| do_motion | If True, advance simulation frames until the pick-up motion is done. |

***

#### `turn_to(self, target: Union[Dict[str, float], int], force: float = 1000, stopping_threshold: float = 0.15, avatar_id: str = "a") -> bool`

Turn the avatar to face a target.
The motion continues until the avatar is either facing the target, overshoots it, or rotates a full 360 degrees.

| Parameter | Description |
| --- | --- |
| avatar_id | The unique ID of the avatar. |
| target | The target position or object ID. |
| force | The force at which the avatar will turn. More force = faster, but might overshoot the target. |
| stopping_threshold | Stop when the avatar is within this many degrees of the target. |

_Returns:_  True if the avatar succeeded in turning to face the target.

***

#### `turn_by(self, angle: float, force: float = 1000, stopping_threshold: float = 0.15, avatar_id: str = "a") -> bool`

Turn the avatar by an angle.
The motion continues until the avatar is either facing the target, overshoots it, or rotates a full 360 degrees.

| Parameter | Description |
| --- | --- |
| avatar_id | The unique ID of the avatar. |
| angle | The angle to turn to in degrees. If > 0, turn clockwise; if < 0, turn counterclockwise. |
| force | The force at which the avatar will turn. More force = faster, but might overshoot the target. |
| stopping_threshold | Stop when the avatar is within this many degrees of the target. |

_Returns:_  True if the avatar succeeded in turning to face the target.

***

#### `go_to(self, target: Union[Dict[str, float], int], turn_force: float = 1000, turn_stopping_threshold: float = 0.15, move_force: float = 80, move_stopping_threshold: float = 0.35, avatar_id: str = "a") -> bool`

Move the avatar to a target position or object.
If the avatar isn't facing the target, it will turn to face it (see `turn_to()`).
The motion continues until the avatar reaches the destination, or if:
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

#### `move_forward_by(self, distance: float, move_force: float = 80, move_stopping_threshold: float = 0.35, avatar_id: str = "a") -> bool`

Move the avatar forward by a distance along the avatar's current forward directional vector.
The motion continues until the avatar reaches the destination, or if:
- The avatar overshot the target.
- The avatar's body collided with a heavy object (mass >= 90)
- The avatar collided with part of the environment (such as a wall).

| Parameter | Description |
| --- | --- |
| avatar_id | The ID of the avatar. |
| distance | The distance that the avatar will travel. If < 0, the avatar will move backwards. |
| move_force | The force at which the avatar will move. More force = faster, but might overshoot the target. |
| move_stopping_threshold | Stop within this distance of the target. |

_Returns:_  True if the avatar arrived at the destination.

***

#### `shake(self, joint_name: str = "elbow_left", axis: str = "pitch", angle: Tuple[float, float] = (20, 30), num_shakes: Tuple[int, int] = (3, 5), force: Tuple[float, float] = (900, 1000), avatar_id: str = "a") -> \ None`

Shake an avatar's arm for multiple iterations.
Per iteration, the joint will bend forward by an angle and then bend back by an angle.
The motion ends when all of the avatar's joints have stopped moving.

| Parameter | Description |
| --- | --- |
| avatar_id | The ID of the avatar. |
| joint_name | The name of the joint. |
| axis | The axis of the joint's rotation. |
| angle | Each shake will bend the joint by a angle in degrees within this range. |
| num_shakes | The avatar will shake the joint a number of times within this range. |
| force | The avatar will add strength to the joint by a value within this range. |

***

#### `rotate_camera_by(self, avatar_id: str = "a", pitch: float = 0, yaw: float = 0, roll: float = 0) -> None`

Rotate an avatar's camera around each axis.
The head of the avatar won't visually rotate (as this could put the avatar off-balance).
Advances the simulation by 1 frame.

| Parameter | Description |
| --- | --- |
| avatar_id | The ID of the avatar. |
| pitch | Pitch (nod your head "yes") the camera by this angle, in degrees. |
| yaw | Yaw (shake your head "no") the camera by this angle, in degrees. |
| roll | Roll (put your ear to your shoulder) the camera by this angle, in degrees. |

***

#### `reset_camera_rotation(self, avatar_id: str = "a") -> None`

Reset the rotation of the avatar's camera.
Advances the simulation by 1 frame.

| Parameter | Description |
| --- | --- |
| avatar_id | The ID of the avatar. |

***

#### `add_overhead_camera(self, position: Dict[str, float], target_object: Union[str, int] = None, cam_id: str = "c", images: str = "all") -> None`

Add an overhead third-person camera to the scene.
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

#### `end(self) -> None`

End the simulation. Terminate the build process.

***

