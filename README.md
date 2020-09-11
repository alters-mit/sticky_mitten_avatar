# Sticky Mitten Avatar API

A high-level API for [TDW's](https://github.com/threedworld-mit/tdw/) [Sticky Mitten Avatar](https://github.com/threedworld-mit/tdw/blob/master/Documentation/misc_frontend/sticky_mitten_avatar.md). 

## Installation

1. [Install TDW](https://github.com/threedworld-mit/tdw/) (make sure you are using the latest version)
2. Clone this repo
3. `cd path/to/sticky_mitten_avatar` (replace `path/to` with the actual path)
4. Install the local `sticky_mitten_avatar` pip module:

| Windows                    | OS X and Linux      |
| -------------------------- | ------------------- |
| `pip3 install -e . --user` | `pip3 install -e .` |

## Usage

### API

**For a detailed API, [read this](Documentation/sma_controller.md).** Use the StickyMittenAvatarController to move an avatar in a scene with a high-level API. 

- At the start of the simulation, the controller caches [static object info](Documentation/static_object_info.md) per object in the scene and [static avatar info](Documentation/body_part_static.md).
- Each API function returns a [TaskStatus](Documentation/task_status.md) indicating whether the action succeeded and if not, why.
- After calling each function, the controller updates its [FrameData](Documentation/frame_data.md). This data can be used to decide what the avatar's next action will be (pick up an object, navigate around a room, etc.)
- Most complex tasks, such as navigation/pathfinding are not implemented in this API because the problem is too unbounded for a simple algorithm. However, given the output data (static object info, static avatar info, and FrameData), an agent equipped with ML data can be trained to do any of these tasks successfully.

### API (low-level)

- For further lower-level documentation, [read these documents](https://github.com/alters-mit/sticky_mitten_avatar/tree/master/Documentation).
- For more information regarding TDW, see the [TDW repo](https://github.com/threedworld-mit/tdw/).
- For more information regarding TDW's low-level Sticky Mitten Avatar API, [read this](https://github.com/threedworld-mit/tdw/blob/master/Documentation/misc_frontend/sticky_mitten_avatar.md).

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
c.reach_for_target(arm=Arm.left, target={"x": 0.1, "y": 0.6, "z": 0.4})
```

...or this:

```python
from sticky_mitten_avatar.test_controller import TestController

class MyController(TestController):
    def my_function(self):
        self.reach_for_target(arm=Arm.left, target={"x": 0.1, "y": 0.6, "z": 0.4})

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

### 0.3.0

#### High-Level

- Each API call returns a `TaskStatus` instead of a `bool`. The `TaskStatus` indicates whether the task was a success and if not, why.
- There is always exactly 1 avatar per scene.
  - Removed `avatar_id` parameter from all API and output data. 
  - `FrameData.avatar_collision` is an `AvatarCollisions` object (was a dictionary mapped to avatar IDs)
  - `StickyMittenAvatarController.static_avatar_data` is a dictionary of `BodyPartStatic` (was a dictionary of dictionaries, mapped to avatar IDs)
- Better formatting for API document headers.
- Cleaned up API section of README document.
- Removed: `fail_state.md`
- `StickyMittenAvatarController.md` (API document) includes all possible `TaskStatus` return values per function.

***

### 0.2.3

#### High-Level

- Added: `StickyMittenAvatarController.tap()`
- `avatar_id` parameter of all API functions in `StickyMittenAvatarController` has a default value of `"a"`
- Renamed: `StickyMittenAvatarController.bend_arm()` to `StickyMittenAvatarController.reach_for_target()`
- Added optional parameter `check_if_possible` to `StickyMittenAvatarController.reach_for_target()`
- `StickyMittenAvatarController` gathers `_id` and `_depth_simple` image passes instead of `_img` and `_id`.
- Fixed: `put_object_in_container.py` doesn't work.
- `FrameData` records audio due to collisions with avatar body parts.
- Renamed: `FrameData.segmentation_image` to `FrameData.id_pass`
- Renamed: `FrameData.depth_map` to `FrameData.depth_pass`
  - `FrameData.depth_pass` can be converted to a grayscale image instead of being a numpy array of floats
- Added: `FrameData.save_images()`
- Added: `FrameData.get_pil_images()`
- Added test controller: `tap.py`
- Added video: `put_object_in_container.mp4`

#### Low-Level

- Renamed: `Avatar.can_bend_to()` to `Avatar.can_reach_target()`
- Fixed: `Avatar.can_bend_to()` is inaccurate.

***

### 0.2.2

#### High-Level

- Made the following functions in `StickyMittenAvatarController` private (added a `_` prefix), thereby hiding them from the API:
  - `_create_avatar()`
  - `get_add_object()` (renamed to `_add_object()`)
  - `get_add_container()` (renamed to `_add_container()`)
  - `_do_joint_motion()`
  - `_stop_avatar()`
  - `_destroy_avatar()`
- Set a default value for the `avatar_id` for most `StickyMittenAvatarController` API calls.
- Added: `StickyMittenAvatarController.static_avatar_data`.
- Added: `StickyMittenAvatar.rotate_camera_by()`.
- Added: `StickyMittenAvatar.reset_camera_rotation()`.
- Removed: `StickyMittenAvatarController.get_container_records()`
- Removed: `StickyMittenAvatarController.on_resp` (functionality can be replicated with `Controller.communite()`)
- Added field `name` to `BodyPartStatic`.
- Added field `audio` to `BodyPartStatic`.
- Moved `BodyPartStatic` to `body_part_static.py`.
- Removed `FrameData.images` and added: `FrameData.segmentation_image` (a PIL image) and `FrameData.depth_map` (a numpy array).
- Added field `avatar_collisions` to `FrameData`. Collisions per avatar between its body parts and other objects or the environment.
- Set the maximum shoulder roll angle to 90 degrees (was 45 degrees).
- Added: `collision_test.py` Test for the avatar listening to collisions.
- Added: `test_controller.py` Initialize a simple scene and an avatar in debug mode. 
- Removed private functions from API documentation.
- Added example code to `FrameData` documentation.
- Various improvements to `StickyMittenAvatar` API documentation.
- Added: `fail_state.md` document to explain fail states.
- Updated `shake_demo.mp4`

#### Low-Level

- Added: `Avatar.can_bend_to()` True if the avatar can bend the arm to the target (assuming no obstructions or other factors).

***

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