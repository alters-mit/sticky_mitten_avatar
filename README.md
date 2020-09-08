# Sticky Mitten Avatar API

A high-level api for TDW TDW's [Sticky Mitten Avatar](https://github.com/threedworld-mit/tdw/blob/master/Documentation/misc_frontend/sticky_mitten_avatar.md). 

## Installation

1. [Install TDW](https://github.com/threedworld-mit/tdw/) (make sure you are using the latest version)
2. Clone this repo
3. `cd path/to/sticky_mitten_avatar` (replace `path/to` with the actual path)
4. Install the local `sticky_mitten_avatar` pip module:

| Windows                    | OS X and Linux      |
| -------------------------- | ------------------- |
| `pip3 install -e . --user` | `pip3 install -e .` |

## Usage

Use the [StickyMittenAvatarController](Documentation/sma_controller.md) to create avatars and move them around the scene with a high-level API. **For a detailed API, [read this](Documentation/sma_controller.md).**

For the API for output data (data received from the build), see **Fields (Output Data)** below.

For further low-level documentation, [read these documents](https://github.com/alters-mit/sticky_mitten_avatar/tree/master/Documentation).

#### General

Each of these functions advance the simulation 1 frame.

| Function                | Description                                                  |
| ----------------------- | ------------------------------------------------------------ |
| `init_scene()`          | Initialize the scene.                                        |
| `add_overhead_camera()` | Add a third-person camera to the scene.                      |
| `end()`                 | Stop the controller and kill the simulation process.         |
| `communicate()`         | Low-level. Send [commands](https://github.com/threedworld-mit/tdw/blob/master/Documentation/api/command_api.md) to the build and receive a response. |

#### Avatar

By default, all of these functions will advance the simulation _n_ frames. Each of them has a success state as well as a [fail state](Documentation/fail_state.md).

| Function            | Description                                     |
| ------------------- | ----------------------------------------------- |
| `bend_arm()`        | Bend the arm of an avatar to a target position. |
| `pick_up()`         | Try to pick up an object.                       |
| `put_down()`        | Put down all held objects.                      |
| `turn_to()`         | Face a target position or object.               |
| `turn_by()`         | Turn by an angle.                               |
| `go_to()`           | Go to a target position or object.              |
| `move_forward_by()` | Move forward by a given distance.               |
| `shake()`           | Shake a joint back and forth.                   |
| `reset_arms()`      | Return the arms to their "neutral" positions.   |
| `stop_avatar()`     | Stop the avatar's movement and rotation.        |

#### Fields (Output Data)

| Field | Description |
| ----- | ----------- |
| `static_object_info`    | [Static object info](Documentation/static_object_info.md) per object in the scene. |
| `static_avatar_info` | [Static avatar info](Documentation/avatar.md#BodyPartStatic) per avatar in the scene. |
| `frame`                 | [Frame data](Documentation/frame_data.md) for the most recent frame. |

#### Commands

You can, if you wish, use [TDW's low-level Command API](https://github.com/threedworld-mit/tdw/blob/master/Documentation/api/command_api.md).

## Controllers

Sub-classes of `StickyMittenAvatarController` have built-in scene setup recipes.

| Controller                                                   | Description                                                  |
| ------------------------------------------------------------ | ------------------------------------------------------------ |
| [StickyMittenAvatarController](Documentation/sma_controller.md) | High-level API controller for sticky mitten avatars. Creates a simple scene. |
| [BoxRoomContainers](Documentation/box_room_containers.md)    | Sub-class of StickyMittenAvatarController. When `init_scene()` is called, it will create a photorealistic room with furniture and two containers with different objects in them. |
| [TestController](Documentation/test_controller.md)           | Output data returned from the build per frame.               |
To use these controllers, do this:

```python
from sticky_mitten_avatar.avatars import Arm
from sticky_mitten_avatar.test_controller import TestController


c = TestController()
c.init_scene()
c.bend_arm(avatar_id="a", arm=Arm.left, target={"x": 0.1, "y": 0.6, "z": 0.4})
```

...or this:

```python
from sticky_mitten_avatar.test_controller import TestController

class MyController(TestController):
    def my_function(self):
        self.bend_arm(avatar_id="a", arm=Arm.left, target={"x": 0.1, "y": 0.6, "z": 0.4})

if __name__ == "__main__":
    c = MyController()
    c.init_scene()
    c.my_function()
```

To do something per-frame, regardless of whether the avatar is in the middle of an action, override the `communicate()` function. See [this controller](https://github.com/alters-mit/sticky_mitten_avatar/blob/master/controllers/put_object_in_container.py), which overrides `communicate()` in order to save an image every frame.

## Examples

All example controllers can be found in: `controllers/`

| Controller                   | Description                                                  |
| ---------------------------- | ------------------------------------------------------------ |
| `put_object_in_container.py` | Put an object in a container.                                |
| `shake_demo.py`              | An avatar shakes two different containers with different audio properties. |
| `put_object_on_table.py`     | _Obsolete._ Put an object on a table using a simple "aiming" algorithm to bend the arm. |

## Tests

| Controller          | Description                               |
| ------------------- | ----------------------------------------- |
| `ik_test.py`        | Test the IK chains of the avatar's arms.  |
| `collision_test.py` | Test the avatar's response to collisions. |

## Utility Scripts

| Script             | Description                                                  |
| ------------------ | ------------------------------------------------------------ |
| `add_model.py`     | Use this script to add create an asset bundle from a prefab and add it to a library in this repo. See:  [AssetBundleCreator](https://github.com/threedworld-mit/tdw/blob/master/Documentation/python/asset_bundle_creator.md). |
| `init_commands.py` | Convert initialization commands into a Sticky Mitten Avatar API scene recipe. |

## Changelog

### 0.2.2

#### High-Level

- Made the following functions in `StickyMittenController` private (added a `_` prefix), thereby hiding them from the API:
  - `_create_avatar()`
  - `get_add_object()` (renamed to `_add_object()`)
  - `get_add_container()` (renamed to `_add_container()`)
  - `_do_joint_motion()`
  - `_stop_avatar()`
  - `_destroy_avatar()`
- Added: `StickyMittenAvatar.static_avatar_data`.
- Removed: `StickyMittenAvatar.get_container_records()`
- Removed: `StickyMittenAvatarController.on_resp` (functionality can be replicated with `Controller.communite()`)
- Added: `test_controller.py` Initialize a simple scene and an avatar in debug mode. 
- Added field `name` to `BodyPartStatic`.
- Added field `avatar_collisions` to `FrameData`. Collisions per avatar between its body parts and other objects or the environment.
- Set the maximum shoulder roll angle to 90 degrees (was 45 degrees).
- Added: `collision_test.py` Test for the avatar listening to collisions.
- Removed private functions from API documentation.
- Added example code to `FrameData` documentation.
- Various improvements to `StickyMittenAvatar` API documentation.
- Updated `shake_demo.mp4`

#### Low-Level

- Added: `Avatar.can_bend_to()` True if the avatar can bend the arm to the target (assuming no obstructions or other factors).

### 0.2.1

#### High-Level

- Improved the overall stability of `shake_demo.py`
- Improved the positional accuracy of arm-bending API calls  by matching the IK parameters more closely to the avatar prefab parameters.
- Fixed: The default speed of `StickyMittenAvatarController.turn_to()` is slower than the turn speed in `StickyMittenAvatarController.go_to()`.
- `StickyMittenAvatarController.bend_arm()` will increase the force and decrease the damper of all joints that are bending. When they are done bending, they will revert to the original values.
- Added: `videos/shake_demo.mp4`

#### Low-Level

- Avatar IK arm chains now include `mitten`, the centerpoint of the mitten.
- `Avatar.is_holding()` return a boolean and the arm holding the item (instead of just a boolean).

***

### 0.2.0

- Parameter `target` in `Avatar.bend_arm` must be a numpy array (previously, could be a numpy array or a list).
- Added: `Avatar.reset_arms()` Set the arms to a "neutral" position.
- Added: `Avatar.set_dummy_ik_goals()` Set "dummy" IK goals with no targets.
- Added: `box_room_containers.py` Creates a photorealistic scene with furniture and containers.
- **Added: `shake_demo.py`. The avatar shakes containers and "listens" to the audio.**
- Renamed: `PhysicsInfo` to `DynamicObjectInfo`
- Added: `FrameData` **Contains image and audio data.**
- Added new fields to `StickyMittenAvatarController`:
  - `frame` Current frame data. 
  - `static_object_info` Static object info per object.
  - Added parameter to `StickyMittenAvatarController` constructor: `audio_playback_mode`
- Added: `StickyMittenAvatar.init_scene()` Initialize a scene.
- Changed the commands returned by `StickyMittenAvatar.get_add_object()`
- Added: `StickyMittenAvatar.get_container_records()` Get records for all container models.
- Added: `StickyMittenAvatar.get_add_container()` Add a container to the scene.
- Added: `StickyMittenAvatar.reset_arms()`  Set the arms to a "neutral" position.
- Added: `StickyMittenAvatarController.shake()` Shake an avatar's joint.
- Added: `StickyMittenAvatarController.destroy_avatar()` Destroy the avatar.
- Added: `StickyMittenAvatarController.end()` End the simulation.
- Added parameter `do_motion` to `StickyMittenAvatar.put_down()`
- Parameter `target` in `StickyMittenAvatar.turn_to()` must be a dictionary (Vector3) or an integer (object ID).
- Added: `StaticObjectInfo`
- Removed: `util.get_collisions()`
- Added utility script: `add_model.py`
- Added utility script: `init_commands.py`
- Added test controller: `tests/ik_test.py`
- Removed test controller: `arm_test.py`
- Moved `put_object_in_container.py` to `controllers/` and adjusted some values to make it work with the improved IK system.
- Moved `put_object_on_table.py` to `controllers/`
- Added asset bundle `shoebox_fused`.
- Added: `audio.csv` Default audio values.
- Added model libraries: `containers.json` and `container_contents.json`
- **Fixed: IK chains for the baby avatar are wrong.**
- Fixed: `util.rotate_point_around()` often returns incorrect values.
- Fixed: `def` headers in documentation sometimes don't contain all parameters.
- Added: `videos/shake_demo.mp4`