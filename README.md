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

#### High-Level

##### General

| Function                | Description                                          |
| ----------------------- | ---------------------------------------------------- |
| `init_scene()`          | Initialize the scene.                                |
| `add_overhead_camera()` | Add a third-person camera to the scene.              |
| `end()`                 | Stop the controller and kill the simulation process. |

##### Avatar

| Function                | Description                                                  |
| ----------------------- | ------------------------------------------------------------ |
| `bend_arm()`            | Bend the arm of an avatar to a target position. |
| `pick_up()`             | Try to pick up an object.                  |
| `put_down()`            | Put down all held objects.                 |
| `turn_to()`             | Face a target position or object.          |
| `go_to()`               | Go to a target position or object.         |
| `shake()`               | Shake a joint back and forth.              |
| `reset_arms()`          | Return the arms to their "neutral" positions.                |
| `stop_avatar()`         | Stop the avatar's movement and rotation.                     |

##### Fields

| Field | Description |
| ----- | ----------- |
| `static_object_info`    | [Static object info](Documentation/static_object_info.md) per object in the scene. |
| `on_resp`               | Do something with the response (output data) per frame.      |
| `frame`                 | [Frame data](Documentation/frame_data.md) for the most recent frame. |

#### Mid-Level

| Function | Description |
| -------- | ----------- |
| `create_avatar()`       | Create an avatar.                                            |
| `get_add_object()`      | Returns a list of commands to add an object to the scene and to set its position, mass, etc. Overrides [`Controller.get_add_object()`](https://github.com/threedworld-mit/tdw/blob/master/Documentation/python/controller.md#get_add_objectself-model_name-str-object_id-int-positionx-0-y-0-z-0-rotationx-0-y-0-z-0-library-str-----dict); returns a list of commands instead of just 1 command. |
| `get_add_container()`   | Similar to `get_add_object()` except that it adds a specialized "container" object and puts small objects in the container. |
| `destroy_avatar()` | Destroy an avatar in the scene. |

#### Low-Level

The [TDW Command API](https://github.com/threedworld-mit/tdw/blob/master/Documentation/api/command_api.md) can be used in conjunction with this API.

| Function            | Description                                                  |
| ------------------- | ------------------------------------------------------------ |
| `communicate()`     | Overrides [`Controller.communicate()`](https://github.com/threedworld-mit/tdw/blob/master/Documentation/python/controller.md#communicateself-commands-uniondict-listdict---list). Includes additional automated functionality. |
| `do_joint_motion()` | Step through the simulation until the joints of all avatars are done moving. |

## API

#### High-Level

| Class                                                        | Description                                                  |
| ------------------------------------------------------------ | ------------------------------------------------------------ |
| [StickyMittenAvatarController](Documentation/sma_controller.md) | High-level API controller for sticky mitten avatars. Creates a simple scene. |
| [BoxRoomContainers](Documentation/box_room_containers.md)    | Sub-class of StickyMittenAvatarController. When `init_scene()` is called, it will create a photorealistic room with furniture and two containers with different objects in them. |
| [FrameData](Documentation/frame_data.md)                     | Output data returned from the build per frame.               |
| [StaticObjectInfo](Documentation/static_object_info.md)      | Static object info (ID, segmentation color, etc.) for a single object. |

#### Low-Level

| Class                                                        | Description                                                  |
| ------------------------------------------------------------ | ------------------------------------------------------------ |
| [Avatar](Documentation/avatar.md)                            | High-level API for a sticky mitten avatar. Do not use this class directly; it is an abstract class. Use the `Baby` class instead (a subclass of `Avatar`). |
| [Baby](Documentation/baby.md)                                | A small sticky mitten avatar.                                |
| [DynamicObjectInfo](Documentation/dynamic_object_info.md)    | Dynamic physics info (position, velocity, etc.) for a single object. |
| [util](Documentation/util.md)                                | Utility functions.                                           |

## Controllers

All controllers can be found in: `controllers/`

| Controller                   | Description                                                  |
| ---------------------------- | ------------------------------------------------------------ |
| `put_object_in_container.py` | Put an object in a container.                                |
| `shake_demo.py`              | An avatar shakes two different containers with different audio properties. |
| `put_object_on_table.py`     | _Obsolete._ Put an object on a table using a simple "aiming" algorithm to bend the arm. |

## Changelog

### 0.2.0

- Added: `Avatar.set_dummy_ik_goals()` Set "dummy" IK goals with no targets.
- Renamed: `PhysicsInfo` to `DynamicObjectInfo`
- Added new fields to `StickyMittenAvatarController`:
  - `frame` Current frame data. 
  - `static_object_info` Static object info per object.
- Added parameter to `StickyMittenAvatarController` constructor: `audio_playback_mode`
- Added: `StickyMittenAvatarController.end_scene_setup()` End scene setup. Cache data. Request output data.
- Added: `StickyMittenAvatarController.shake()` Shake an avatar's joint.
- Added: `StaticObjectInfo`
- Added: `FrameData` **Contains image and audio data.**
- Removed: `util.get_collisions()`
- Fixed: `def` headers in documentation.
- Fixed: Bad IK chains for the baby avatar.