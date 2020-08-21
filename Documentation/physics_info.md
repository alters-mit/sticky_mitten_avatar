# `sticky_mitten_avatar/physics_info.py`

## `PhysicsInfo`

`from tdw.sticky_mitten_avatar.physics_info import PhysicsInfo`

Dynamic physics info (position, velocity, etc.) for a single object.
Contains the following information as numpy arrays:

- `position`
- `forward`
- `rotation`
- `velocity`
- `angular_velocity`
- `sleeping` (boolean)

This class is used in the StickyMittenAvatarController.

***

#### `__init__(self, o_id: int, tran: Transforms, rigi: Rigidbodies, tr_index: int)`


| Parameter | Description |
| --- | --- |
| o_id | The ID of the object. |
| tran | Transforms data. |
| rigi | Rigidbodies data. |
| tr_index | The index of the object in the Transforms object. |

***

