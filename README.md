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

```python
from sticky_mitten_avatar import StickyMittenAvatarController, Arm

c = StickyMittenAvatarController()
c.init_scene()
task_status = c.reach_for_target(arm=Arm.left, target={"x": 0.1, "y": 0.6, "z": 0.4})
print(task_status) # TaskStatus.success
c.end()
```

### API

**For a detailed API, [read this](Documentation/sma_controller.md).** Use the StickyMittenAvatarController to move an avatar in a scene with a high-level API. 

- At the start of the simulation, the controller caches [static object info](Documentation/static_object_info.md) per object in the scene and [static avatar info](Documentation/body_part_static.md).
- Each API function returns a [TaskStatus](Documentation/task_status.md) indicating whether the action succeeded and if not, why.
- After calling each function, the controller updates its [FrameData](Documentation/frame_data.md). This data can be used to decide what the avatar's next action will be (pick up an object, navigate around a room, etc.)
- Most complex tasks, such as navigation/pathfinding are not implemented in this API because the problem is too unbounded for a simple algorithm. However, given the output data (static object info, static avatar info, and FrameData), an agent equipped with ML data can be trained to do any of these tasks successfully.

### API (low-level)

- For more information regarding TDW, see the [TDW repo](https://github.com/threedworld-mit/tdw/).
- For more information regarding TDW's low-level Sticky Mitten Avatar API, [read this](https://github.com/threedworld-mit/tdw/blob/master/Documentation/misc_frontend/sticky_mitten_avatar.md).

## How to write your controller

You can write your controller like this:

```python
from sticky_mitten_avatar import StickyMittenAvatarController, Arm

c = StickyMittenAvatarController()
c.init_scene()
task_status = c.reach_for_target(arm=Arm.left, target={"x": 0.1, "y": 0.6, "z": 0.4})
print(task_status) # TaskStatus.success
c.end()
```

...or this, with your own class:

```python
from sticky_mitten_avatar import StickyMittenAvatarController, Arm

class MyController(StickyMittenAvatarController):
    def my_function(self):
        return self.reach_for_target(arm=Arm.left, target={"x": 0.1, "y": 0.6, "z": 0.4})

if __name__ == "__main__":
    c = MyController()
    c.init_scene()
    print(c.my_function()) # TaskStatus.success
    c.end()
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

| Controller                 | Description                                                  |
| -------------------------- | ------------------------------------------------------------ |
| `ik_test.py`               | Test the IK chains of the avatar's arms.                     |
| `collision_test.py`        | Test the avatar's response to collisions.                    |
| `turn_test.py`             | Test avatar turning.                                         |
| `composite_object_test.py` | Test if the avatar can grasp a sub-object of a composite object. |

## Utility Scripts

| Script                      | Description                                                  |
| --------------------------- | ------------------------------------------------------------ |
| `add_model.py`              | Use this script to add create an asset bundle from a prefab and add it to a library in this repo. See:  [AssetBundleCreator](https://github.com/threedworld-mit/tdw/blob/master/Documentation/python/asset_bundle_creator.md). |
| `composite_object_audio.py` | Get default audio parameters for sub-objects of composite objects. |
| `container_dimensions.py`   | Calculate container dimensions.                              |

## Changelog

See [Changelog](changelog.md).