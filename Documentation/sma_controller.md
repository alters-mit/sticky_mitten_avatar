# StickyMittenAvatarController

`from sticky_mitten_avatar import StickyMittenAvatarController`StickyMittenAvatarController`

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
# Print each object ID and segmentation color.
for object_id in c.static_object_info:
    object_info = c.static_object_info(object_id)
    print(object_id, object_info.segmentation_color)
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
# Print each body part ID and segmentation color.
for body_part_id in c.static_avatar_data:
    body_part = c.static_avatar_data[body_part_id]
    print(body_part_id, body_part.segmentation_color).
```

- `occupancy_map` A numpy array of positions in the scene and whether they are occupied.
   If `scene` or `layout` is None, then this is None.
   Shape is `(width, length)` Data type = `int`. 0 = occupied. 1 = free. 2 = outside of the scene.
   A position is occupied if there is an object (such as a table) or environment obstacle (such as a wall) within 0.25 meters of the position.

   This is static data for the _initial_ scene occupancy_maps. It won't update if an object's position changes.

   This is _not_ a navigation map. If there is a gap between positions, the avatar might still be able to go from one to the other.

   Images of each occupancy map can be found [here](https://github.com/alters-mit/sticky_mitten_avatar/tree/master/images/occupancy_maps). Key: Red = Free position. Blue = Free position where a target object or container can be placed.
   The files are named `<scene>_<layout>` (the lettered variants of each scene are different only visually, so the occupancy maps of `scene 1a, layout 0`, `scene 1b, layout 0`, and `scene 1c, layout 0` are exactly the same, but the occupancy map of `scene 1a, layout 1` is different.

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

***

#### \_\_init\_\_

**`def __init__(self, port: int = 1071, launch_build: bool = True, demo: bool = False, id_pass: bool = True, screen_width: int = 256, screen_height: int = 256, debug: bool = False)`**

| Parameter | Description |
| --- | --- |
| port | The port number. |
| launch_build | If True, automatically launch the build. If False, you will need to launch the build yourself (for example, from a Docker container). |
| demo | If True, this is a demo controller. All frames will be rendered. |
| id_pass | If True, add the segmentation color pass to the [`FrameData`](frame_data.md). The simulation will run somewhat slower. |
| screen_width | The width of the screen in pixels. |
| screen_height | The height of the screen in pixels. |
| debug | If True, debug mode will be enabled. The console will output print statements, the simulator will draw targets for the avatar's mittens, and the controller will generate image plots of arm movements. |

***

### Scene Setup

_These functions should be sent at the start of the simulation. They advance the simulation by 1 frame and `StickyMittenAvatarController.frame` will reflect the state of that frame._

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
| 1a, 1b, 1c | 0, 1, 2 | 0, 1, 2, 3, 4, 5, 6 |
| 2a, 2b, 2c | 0, 1, 2 | 0, 1, 2, 3, 4, 5, 6, 7, 8 |
| 4a, 4b, 4c | 0, 1, 2 | 0, 1, 2, 3, 4, 5, 6, 7 |
| 5a, 5b, 5c | 0, 1, 2 | 0, 1, 2, 3 |

Images of each scene+layout combination can be found [here](https://github.com/alters-mit/sticky_mitten_avatar/tree/master/Documentation/images/floorplans).

You can safely call `init_scene()` more than once to reset the simulation.

| Parameter | Description |
| --- | --- |
| scene | The name of an interior floorplan scene. If None, the controller will load a simple empty room. Each number (1, 2, etc.) has a different shape, different rooms, etc. Each letter (a, b, c) is a cosmetically distinct variant with the same floorplan. |
| layout | The furniture layout of the floorplan. Each number (0, 1, 2) will populate the floorplan with different furniture in different positions. If None, the controller will load a simple empty room. |
| room | The index of the room that the avatar will spawn in the center of. If `scene` or `layout` is None, the avatar will spawn in at (0, 0, 0). If `room == -1` the room will be chosen randomly. |

#### add_overhead_camera

**`def add_overhead_camera(self, position: Dict[str, float], target_object: Union[str, int] = None, cam_id: str = "c", images: str = "all") -> None`**

Add an overhead third-person camera to the scene. This is meant only for demo or debugging purposes, _not_ for gathering multiple image passes.

| Parameter | Description |
| --- | --- |
| cam_id | The ID of the camera. |
| target_object | Always point the camera at this object or avatar. |
| position | The position of the camera. |
| images | Image capture behavior. Choices: `"cam"` (only this camera captures images); `"all"` (avatars currently in the scene and this camera capture images); `"avatars"` (only the avatars currently in the scene capture images) |

***

### Movement

_These functions move or turn the avatar. These functions advance the simulation by many frames, depending on the nature of the action. `StickyMittenAvatarController.frame` will reflect the simulation state at the final frame._

#### turn_to

**`def turn_to(self, target: Union[Dict[str, float], int], force: float = 1000, stopping_threshold: float = 0.15, num_attempts: int = 200, sub_action: bool = False, stop_on_collision: bool = True) -> TaskStatus`**

Turn the avatar to face a target position or object.

Possible [return values](task_status.md):

- `success` (The avatar turned to face the target.)
- `too_long` (The avatar made more attempts to turn than `num_attempts`.)
- `collided_with_something_heavy` (if `stop_on_collision == True`)
- `collided_with_environment` (if `stop_on_collision == True`)


| Parameter | Description |
| --- | --- |
| target | Either the target position or the ID of the target object. |
| force | The force at which the avatar will turn. More force = faster, but might overshoot the target. |
| stopping_threshold | Stop when the avatar is within this many degrees of the target. |
| num_attempts | The avatar will apply more angular force this many times to complete the turn before giving up. |
| stop_on_collision | If True, stop turning when the avatar collides with a large object (mass > 90) or the environment (e.g. a wall). |
| sub_action | If True, this is a sub-action and is being called from another API call. Sub-actions won't render images. Frontend users should always set this to False (the default value). |

_Returns:_  A `TaskStatus` indicating whether the avatar turned successfully and if not, why.

#### turn_by

**`def turn_by(self, angle: float, force: float = 1000, stopping_threshold: float = 0.15, num_attempts: int = 200, stop_on_collision: bool = True) -> TaskStatus`**

Turn the avatar by an angle.

Possible [return values](task_status.md):

- `success` (The avatar turned by the angle.)
- `too_long` (The avatar made more attempts to turn than `num_attempts`.)
- `collided_with_something_heavy` (if `stop_on_collision == True`)
- `collided_with_environment` (if `stop_on_collision == True`)


| Parameter | Description |
| --- | --- |
| angle | The angle to turn to in degrees. If > 0, turn clockwise; if < 0, turn counterclockwise. |
| force | The force at which the avatar will turn. More force = faster, but might overshoot the target. |
| stopping_threshold | Stop when the avatar is within this many degrees of the target. |
| stop_on_collision | If True, stop turning when the avatar collides with a large object (mass > 90) or the environment (e.g. a wall). |
| num_attempts | The avatar will apply more angular force this many times to complete the turn before giving up. |

_Returns:_  A `TaskStatus` indicating whether the avatar turned successfully and if not, why.

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
| stop_on_collision | If True, stop moving when the avatar collides with a large object (mass > 90) or the environment (e.g. a wall). |
| turn | If True, try turning to face the target before moving. |
| num_attempts | The avatar will apply more force this many times to complete the turn before giving up. |

_Returns:_   A `TaskStatus` indicating whether the avatar arrived at the target and if not, why.

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
| stop_on_collision | If True, stop moving when the avatar collides with a large object (mass > 90) or the environment (e.g. a wall). |
| num_attempts | The avatar will apply more force this many times to complete the turn before giving up. |

_Returns:_  A `TaskStatus` indicating whether the avatar moved forward by the distance and if not, why.

***

### Arm Articulation

_These functions move and bend the joints of the avatar's arms. These functions advance the simulation by many frames, depending on the nature of the action. `StickyMittenAvatarController.frame` will reflect the simulation state at the final frame._

#### reach_for_target

**`def reach_for_target(self, arm: Arm, target: Dict[str, float], check_if_possible: bool = True, stop_on_mitten_collision: bool = True, precision: float = 0.05, absolute: bool = False, sub_action: bool = False) -> TaskStatus`**

Bend an arm joints of an avatar to reach for a target position.
By default, the target is relative to the avatar's position and rotation.

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
| target | The target position for the mitten. |
| stop_on_mitten_collision | If true, the arm will stop bending if the mitten collides with an object other than the target object. |
| check_if_possible | If True, before bending the arm, check if the mitten can reach the target assuming no obstructions; if not, don't try to bend the arm. |
| precision | The precision of the action. If the mitten is this distance or less away from the target position, the action returns `success`. A greater value means a less precise motion, which means the action might end sooner. |
| absolute | If True, `target` is in absolute world coordinates. If False, `target` is in coordinates relative to the avatar's position and rotation. |
| sub_action | If True, this is a sub action and is being called from another API call. Sub-actions won't render images. Frontend users should always set this to False (the default value). |

_Returns:_  A `TaskStatus` indicating whether the avatar can reach the target and if not, why.

#### grasp_object

**`def grasp_object(self, object_id: int, arm: Arm, check_if_possible: bool = True, stop_on_mitten_collision: bool = True, precision: float = 0.05, sub_action: bool = False) -> TaskStatus`**

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


| Parameter | Description |
| --- | --- |
| object_id | The ID of the target object. |
| arm | The arm of the mitten that will try to grasp the object. |
| stop_on_mitten_collision | If true, the arm will stop bending if the mitten collides with an object. |
| check_if_possible | If True, before bending the arm, check if the mitten can reach the target assuming no obstructions; if not, don't try to bend the arm. |
| precision | The precision of the action. If the mitten is this distance or less away from the target position, the action returns `success`. A greater value means a less precise motion, which means the action might end sooner. |
| sub_action | If True, this is a sub-action and is being called from another API call. Sub-actions won't render images.Frontend users should always set this to False (the default value). |

_Returns:_  A `TaskStatus` indicating whether the avatar picked up the object and if not, why.

#### drop

**`def drop(self, arm: Arm, reset_arm: bool = True, precision: float = 0.1, sub_action: bool = False) -> TaskStatus`**

Drop any held objects held by the arm. Reset the arm to its neutral position.

Possible [return values](task_status.md):

- `success` (The avatar's arm dropped all objects held by the arm (this will be `success` even if there were no objects) asnd if the avatar's arm reset (if applicable).
- `no_longer_bending` (The arm stopped bending before it reset, possibly due to an obstacle in the way.)


| Parameter | Description |
| --- | --- |
| arm | The arm that will drop any held objects. |
| reset_arm | If True, reset the arm's positions to "neutral". |
| precision | The precision of the action. If the angles of each joint are less than this value, the action returns `success`. A greater value means a less precise motion, which means the action might end sooner. |
| sub_action | If True, this is a sub-action and is being called from another API call. Sub-actions won't render images. Frontend users should always set this to False (the default value). |

_Returns:_  A `TaskStatus` indicating whether the avatar dropped all objects held by the arm and reset the arm (if applicable).

#### reset_arm

**`def reset_arm(self, arm: Arm, precision: float = 0.1, sub_action: bool = False) -> TaskStatus`**

Reset an avatar's arm to its neutral positions.

Possible [return values](task_status.md):

- `success` (The arm reset to very close to its initial position.)
- `no_longer_bending` (The arm stopped bending before it reset, possibly due to an obstacle in the way.)

| Parameter | Description |
| --- | --- |
| arm | The arm that will be reset. |
| precision | The precision of the action. If the angles of each joint are less than this value, the action returns `success`. A greater value means a less precise motion, which means the action might end sooner. |
| sub_action | If True, this is a sub-action and is being called from another API call. Sub-actions won't render images. Frontend users should always set this to False (the default value). |

#### put_in_container

**`def put_in_container(self, object_id: int, container_id: int, arm: Arm) -> TaskStatus`**

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


| Parameter | Description |
| --- | --- |
| object_id | The ID of the object that the avatar will try to put in the container. |
| container_id | The ID of the container. To determine if an object is a container, see [`StaticObjectInfo.container`](static_object_info.md). |
| arm | The arm that will try to pick up the object. |

_Returns:_  A `TaskStatus` indicating whether the avatar put the object in the container and if not, why.

***

### Camera

_These functions adjust the avatar's camera orientation. They advance the simulation by 1 frame and `StickyMittenAvatarController.frame` will reflect the state of that frame._

#### rotate_camera_by

**`def rotate_camera_by(self, pitch: float = 0, yaw: float = 0) -> None`**

Rotate an avatar's camera. The head of the avatar won't visually rotate because it would cause the entire avatar to tilt.

| Parameter | Description |
| --- | --- |
| pitch | Pitch (nod your head "yes") the camera by this angle, in degrees. |
| yaw | Yaw (shake your head "no") the camera by this angle, in degrees. |

#### reset_camera_rotation

**`def reset_camera_rotation(self) -> None`**

Reset the rotation of the avatar's camera.

***

### Misc.

_These are utility functions that won't advance the simulation by any frames._

#### end

**`def end(self) -> None`**

End the simulation. Terminate the build process.

#### get_occupancy_position

**`def get_occupancy_position(self, i: int, j: int) -> Tuple[float, float]`**

Converts the position (i, j) in the occupancy map to (x, z) coordinates.


| Parameter | Description |
| --- | --- |
| i | The i coordinate in the occupancy map. |
| j | The j coordinate in the occupancy map. |

_Returns:_  Tuple: x coordinate; z coordinate.

***

### Low-level

_These are low-level functions that you are unlikely to ever need to use._

#### communicate

**`def communicate(self, commands: Union[dict, List[dict]]) -> List[bytes]`**

Use this function to send low-level TDW API commands and receive low-level output data. See: [`Controller.communicate()`](https://github.com/threedworld-mit/tdw/blob/master/Documentation/python/controller.md)

You shouldn't ever need to use this function, but you might see it in some of the example controllers because they might require a custom scene setup.


| Parameter | Description |
| --- | --- |
| commands | Commands to send to the build. See: [Command API](https://github.com/threedworld-mit/tdw/blob/master/Documentation/api/command_api.md). |

_Returns:_  The response from the build as a list of byte arrays. See: [Output Data](https://github.com/threedworld-mit/tdw/blob/master/Documentation/api/output_data.md).

***

