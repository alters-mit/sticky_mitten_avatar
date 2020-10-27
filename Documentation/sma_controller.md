# `sma_controller.py`

## `StickyMittenAvatarController(FloorplanController)`

`from sticky_mitten_avatar import StickyMittenAvatarController`

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

- `segmentation_color_to_id` A dictionary. Key = a hashable representation of the object's segmentation color.
  Value = The object ID. See `static_object_info` for a dictionary mapped to object ID with additional data.

```python
for hashable_color in c.segmentation_color_to_id:
    object_id = c.segmentation_color_to_id[hashable_color]
```

  To convert an RGB array to a hashable integer, see: [`TDWUtils.color_to_hashable()`](https://github.com/threedworld-mit/tdw/blob/master/Documentation/python/tdw_utils.md).

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
print(c.get_occupancy_position(37, 16)) # (1.5036439895629883, -0.42542076110839844)
```

- `goal_positions` A dictionary of possible goal positions.
  Format: `{room_index: "model_name": [pos0, pos1, pos2]}`

```python
from sticky_mitten_avatar import StickyMittenAvatarController

c = StickyMittenAvatarController()
c.init_scene(scene="2a", layout=1)
for room in c.goal_positions:
    print(f"Room {room}:") # Room 1:
    for model_name in c.goal_positions[room]:
        print(model_name, c.goal_positions[room][model_name]) # ligne_roset_armchair [[4, 10]]
```

## Functions

***

#### \_\_init\_\_

**`def __init__(self, port: int = 1071, launch_build: bool = True, demo: bool = False, id_pass: bool = True, audio: bool = False, screen_width: int = 256, screen_height: int = 256)`**


| Parameter | Description |
| --- | --- |
| port | The port number. |
| launch_build | If True, automatically launch the build. |
| demo | If True, this is a demo controller. The build will play back audio and set a slower framerate and physics time step. |
| id_pass | If True, add the segmentation color pass to the [`FrameData`](frame_data.md). The simulation will run somewhat slower. |
| audio | If True, include audio data in the FrameData. |
| screen_width | The width of the screen in pixels. |
| screen_height | The height of the screen in pixels. |

***

#### init_scene

**`def init_scene(self, scene: str = None, layout: int = None, room: int = -1) -> None`**

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
| 1a, 1b, or 1c | 0, 1, or 2 | 0, 1, 2, 3, 4, 5, 6 |
| 2a, 2b, or 2c | 0, 1, or 2 | 0, 1, 2, 3, 4, 5, 6, 7, 8 |
| 4a, 4b, or 4c | 0, 1, or 2 | 0, 1, 2, 3, 4, 5, 6, 7 |
| 5a, 5b, or 5c | 0, 1, or 2 | 0, 1, 2, 3 |
You can safely call `init_scene()` more than once to reset the simulation.

| Parameter | Description |
| --- | --- |
| scene | The name of an interior floorplan scene. If None, the controller will load a simple empty room. |
| layout | The furniture layout of the floorplan. If None, the controller will load a simple empty room. |
| room | The index of the room that the avatar will spawn in the center of. If `scene` or `layout` is None, the avatar will spawn in at (0, 0, 0). If `room == -1` the room will be chosen randomly. |

***

#### communicate

**`def communicate(self, commands: Union[dict, List[dict]]) -> List[bytes]`**

Overrides [`Controller.communicate()`](https://github.com/threedworld-mit/tdw/blob/master/Documentation/python/controller.md).
Before sending commands, append any automatically-added commands (such as arm-bending or arm-stopping).
If there is a third-person camera, append commands to look at a target (see `add_overhead_camera()`).
After receiving a response from the build, update the `frame` data.

| Parameter | Description |
| --- | --- |
| commands | Commands to send to the build. |

_Returns:_  The response from the build.

***

#### reach_for_target

**`def reach_for_target(self, arm: Arm, target: Dict[str, float], do_motion: bool = True, check_if_possible: bool = True, stop_on_mitten_collision: bool = True, precision: float = 0.05) -> TaskStatus`**

Bend an arm joints of an avatar to reach for a target position.
Possible [return values](task_status.md):
- `success` (The avatar's arm's mitten reached the target position.)
- `too_close_to_reach`
- `too_far_to_reach`
- `behind_avatar`
- `no_longer_bending`
- `mitten_collision` (If `stop_if_mitten_collision == True`)

| Parameter | Description |
| --- | --- |
| arm | The arm (left or right). |
| target | The target position for the mitten relative to the avatar. |
| do_motion | If True, advance simulation frames until the pick-up motion is done. |
| stop_on_mitten_collision | If true, the arm will stop bending if the mitten collides with an object other than the target object. |
| check_if_possible | If True, before bending the arm, check if the mitten can reach the target assuming no obstructions; if not, don't try to bend the arm. |
| precision | The precision of the action. If the mitten is this distance or less away from the target position, the action returns `success`. |

_Returns:_  A `TaskStatus` indicating whether the avatar can reach the target and if not, why.

***

#### grasp_object

**`def grasp_object(self, object_id: int, arm: Arm, do_motion: bool = True, check_if_possible: bool = True, stop_on_mitten_collision: bool = True) -> TaskStatus`**

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

| Parameter | Description |
| --- | --- |
| object_id | The ID of the target object. |
| do_motion | If True, advance simulation frames until the pick-up motion is done. |
| arm | The arm of the mitten that will try to grasp the object. |
| stop_on_mitten_collision | If true, the arm will stop bending if the mitten collides with an object. |
| check_if_possible | If True, before bending the arm, check if the mitten can reach the target assuming no obstructions; if not, don't try to bend the arm. |

_Returns:_  A `TaskStatus` indicating whether the avatar picked up the object and if not, why.

***

#### drop

**`def drop(self, arm: Arm, reset_arm: bool = True, do_motion: bool = True) -> TaskStatus`**

Drop any held objects held by the arm. Reset the arm to its neutral position.
Possible [return values](task_status.md):
- `success` (The avatar's arm dropped all objects held by the arm.)

| Parameter | Description |
| --- | --- |
| arm | The arm that will drop any held objects. |
| reset_arm | If True, reset the arm's positions to "neutral". |
| do_motion | If True, advance simulation frames until the pick-up motion is done. |

***

#### reset_arm

**`def reset_arm(self, arm: Arm, do_motion: bool = True) -> TaskStatus`**

Reset an avatar's arm to its neutral positions.
Possible [return values](task_status.md):
- `success` (The arm reset to very close to its initial position.)
- `no_longer_bending` (The arm stopped bending before it reset, possibly due to an obstacle in the way.)

| Parameter | Description |
| --- | --- |
| arm | The arm that will be reset. |
| do_motion | If True, advance simulation frames until the pick-up motion is done. |

***

#### turn_to

**`def turn_to(self, target: Union[Dict[str, float], int], force: float = 1000, stopping_threshold: float = 0.15, num_attempts: int = 200) -> TaskStatus`**

Turn the avatar to face a target position or object.
Possible [return values](task_status.md):
- `success` (The avatar turned to face the target.)
- `too_long` (The avatar made more attempts to turn than `num_attempts`.)

| Parameter | Description |
| --- | --- |
| target | Either the target position or the ID of the target object. |
| force | The force at which the avatar will turn. More force = faster, but might overshoot the target. |
| stopping_threshold | Stop when the avatar is within this many degrees of the target. |
| num_attempts | The avatar will apply more angular force this many times to complete the turn before giving up. |

_Returns:_  A `TaskStatus` indicating whether the avatar turned successfully and if not, why.

***

#### turn_by

**`def turn_by(self, angle: float, force: float = 1000, stopping_threshold: float = 0.15, num_attempts: int = 200) -> TaskStatus`**

Turn the avatar by an angle.
Possible [return values](task_status.md):
- `success` (The avatar turned by the angle.)
- `too_long` (The avatar made more attempts to turn than `num_attempts`.)

| Parameter | Description |
| --- | --- |
| angle | The angle to turn to in degrees. If > 0, turn clockwise; if < 0, turn counterclockwise. |
| force | The force at which the avatar will turn. More force = faster, but might overshoot the target. |
| stopping_threshold | Stop when the avatar is within this many degrees of the target. |
| num_attempts | The avatar will apply more angular force this many times to complete the turn before giving up. |

_Returns:_  A `TaskStatus` indicating whether the avatar turned successfully and if not, why.

***

#### go_to

**`def go_to(self, target: Union[Dict[str, float], int], turn_force: float = 1000, move_force: float = 80, turn_stopping_threshold: float = 0.15, move_stopping_threshold: float = 0.35, stop_on_collision: bool = True, turn: bool = True, num_attempts: int = 200) -> TaskStatus`**

Move the avatar to a target position or object.
Possible [return values](task_status.md):
- `success` (The avatar arrived at the target.)
- `too_long` (The avatar made more attempts to move or to turn than `num_attempts`.)
- `overshot`
- `collided_with_something_heavy` (if `stop_on_collision == True`)
- `collided_with_environment` (if `stop_on_collision == True`)

| Parameter | Description |
| --- | --- |
| target | Either the target position or the ID of the target object. |
| turn_force | The force at which the avatar will turn. More force = faster, but might overshoot the target. |
| turn_stopping_threshold | Stop when the avatar is within this many degrees of the target. |
| move_force | The force at which the avatar will move. More force = faster, but might overshoot the target. |
| move_stopping_threshold | Stop within this distance of the target. |
| stop_on_collision | If True, stop moving when the object collides with a large object (mass > 90) or the environment (e.g. a wall). |
| turn | If True, try turning to face the target before moving. |
| num_attempts | The avatar will apply more force this many times to complete the turn before giving up. |

_Returns:_   A `TaskStatus` indicating whether the avatar arrived at the target and if not, why.

***

#### move_forward_by

**`def move_forward_by(self, distance: float, move_force: float = 80, move_stopping_threshold: float = 0.35, stop_on_collision: bool = True, num_attempts: int = 200) -> TaskStatus`**

Move the avatar forward by a distance along the avatar's current forward directional vector.
Possible [return values](task_status.md):
- `success` (The avatar moved forward by the distance.)
- `too_long` (The avatar made more attempts to move than `num_attempts`.)
- `overshot`
- `collided_with_something_heavy` (if `stop_on_collision == True`)
- `collided_with_environment` (if `stop_on_collision == True`)

| Parameter | Description |
| --- | --- |
| distance | The distance that the avatar will travel. If < 0, the avatar will move backwards. |
| move_force | The force at which the avatar will move. More force = faster, but might overshoot the target. |
| move_stopping_threshold | Stop within this distance of the target. |
| stop_on_collision | If True, stop moving when the object collides with a large object (mass > 90) or the environment (e.g. a wall). |
| num_attempts | The avatar will apply more force this many times to complete the turn before giving up. |

_Returns:_  A `TaskStatus` indicating whether the avatar moved forward by the distance and if not, why.

***

#### shake

**`def shake(self, joint_name: str = "elbow_left", axis: str = "pitch", angle: Tuple[float, float] = (20, 30), num_shakes: Tuple[int, int] = (3, 5), force: Tuple[float, float] = (900, 1000)) -> TaskStatus`**

Shake an avatar's arm for multiple iterations.
Per iteration, the joint will bend forward by an angle and then bend back by an angle.
The motion ends when all of the avatar's joints have stopped moving.
Possible [return values](task_status.md):
- `success`
- `bad_joint`

| Parameter | Description |
| --- | --- |
| joint_name | The name of the joint. |
| axis | The axis of the joint's rotation. |
| angle | Each shake will bend the joint by a angle in degrees within this range. |
| num_shakes | The avatar will shake the joint a number of times within this range. |
| force | The avatar will add strength to the joint by a value within this range. |

_Returns:_  A `TaskStatus` indicating whether the avatar shook the joint and if not, why.

***

#### put_in_container

**`def put_in_container(self, object_id: int, container_id: int, arm: Arm, num_attempts: int = 10) -> TaskStatus`**

Try to put an object in a container.
1. The avatar will grasp the object and a container via `grasp_object()` if it isn't holding them already.
2. The avatar will lift the object up and then over the container via `reach_for_target()`
3. The avatar will make multiple attempts to position the object over the container via `reach_for_target()` plus some backend-only logic.
4. The avatar will `drop()` the object into the container.
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

| Parameter | Description |
| --- | --- |
| object_id | The ID of the object that the avatar will try to put in the container. |
| container_id | The ID of the container. To determine if an object is a container, see [`StaticObjectInfo.container')(static_object_info.md). |
| arm | The arm that will try to pick up the object. |
| num_attempts | Make this many attempts to re-position the object above the container. |

_Returns:_  A `TaskStatus` indicating whether the avatar put the object in the container and if not, why.

***

#### pour_out_container

**`def pour_out_container(self, arm: Arm) -> TaskStatus`**

Pour out the contents of a container held by the arm.
Assuming that the arm is holding a container, its wrist will twist and the arm will lift.
If after doing this there are still objects in the container, the avatar will shake the container.
This action continues until the arm and the objects in the container have stopped moving.
Possible [return values](task_status.md):
- `success` (The container held by the arm is now empty.)
- `not_a_container`
- `empty_container`
- `still_in_container`

| Parameter | Description |
| --- | --- |
| arm | The arm holding the container. |

_Returns:_  A `TaskStatus` indicating whether the avatar poured all objects out of the container and if not, why.

***

#### rotate_camera_by

**`def rotate_camera_by(self, pitch: float = 0, yaw: float = 0) -> None`**

Rotate an avatar's camera around each axis.
The head of the avatar won't visually rotate, as this could put the avatar off-balance.
Advances the simulation by 1 frame.

| Parameter | Description |
| --- | --- |
| pitch | Pitch (nod your head "yes") the camera by this angle, in degrees. |
| yaw | Yaw (shake your head "no") the camera by this angle, in degrees. |

***

#### reset_camera_rotation

**`def reset_camera_rotation(self) -> None`**

Reset the rotation of the avatar's camera.
Advances the simulation by 1 frame.

***

#### add_overhead_camera

**`def add_overhead_camera(self, position: Dict[str, float], target_object: Union[str, int] = None, cam_id: str = "c", images: str = "all") -> None`**

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

#### end

**`def end(self) -> None`**

End the simulation. Terminate the build process.

***

#### get_occupancy_position

**`def get_occupancy_position(self, i: int, j: int) -> Tuple[float, float]`**

Converts the position (i, j) in the occupancy map to (x, z) coordinates.

| Parameter | Description |
| --- | --- |
| i | The i coordinate in the occupancy map. |
| j | The j coordinate in the occupancy map. |

_Returns:_  Tuple: x coordinate; z coordinate.

***

