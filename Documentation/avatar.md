# `sticky_mitten_avatar/avatars/avatar.py`

## `Arm(Enum)`

`from tdw.sticky_mitten_avatar.avatars.avatar import Arm`

The side that an arm is on.

Enum values:

- `left`
- `right`

***

## `BodyPartStatic`

`from tdw.sticky_mitten_avatar.avatars.avatar import BodyPartStatic`

Static data for a body part in an avatar.

***

#### `__init__(self, o_id: int, color: Tuple[float, float, float], name: str)`


| Parameter | Description |
| --- | --- |
| o_id | The object ID of the part. |
| color | The segmentation color of the part. |
| name | The name of the body part. |

***

## `Joint`

`from tdw.sticky_mitten_avatar.avatars.avatar import Joint`

A joint, a side, and an axis.

***

#### `__init__(self, part: str, arm: str, axis: str)`


| Parameter | Description |
| --- | --- |
| part | The name of the body part. |
| axis | The axis of rotation. |
| arm | The arm that the joint is attached to. |

***

#### `__init__(self, target: Union[np.array, list, None], pick_up_id: int = None)`


| Parameter | Description |
| --- | --- |
| pick_up_id | If not None, the ID of the object to pick up. |
| target | The target position of the mitten. |

***

## `Avatar(ABC)`

`from tdw.sticky_mitten_avatar.avatars.avatar import Avatar`

High-level API for a sticky mitten avatar.
Do not use this class directly; it is an abstract class. Use the `Baby` class instead (a subclass of `Avatar`).

Fields:

- `id` The ID of the avatar.
- `body_parts_static` Static body parts data. Key = the name of the part. See `BodyPartsStatic`
- `frame` Dynamic info for the avatar on this frame, such as its position. See `tdw.output_data.AvatarStickyMitten`

***

#### `__init__(self, resp: List[bytes], avatar_id: str = "a", debug: bool = False)`


| Parameter | Description |
| --- | --- |
| resp | The response from the build after creating the avatar. |
| avatar_id | The ID of the avatar. |
| debug | If True, print debug statements. |

***

#### `can_bend_to(self, target: np.array, arm: Arm) -> bool`


| Parameter | Description |
| --- | --- |
| target | The target position. |
| arm | The arm that is bending to the target. |

_Returns:_  True if it is possible to move the mitten to the target.

***

#### `bend_arm(self, arm: Arm, target: np.array, target_orientation: np.array = None) -> List[dict]`

Get an IK solution to move a mitten to a target position.

| Parameter | Description |
| --- | --- |
| arm | The arm (left or right). |
| target | The target position for the mitten. |
| target_orientation | Target IK orientation. Usually you should leave this as None (the default). |

_Returns:_  A list of commands to begin bending the arm.

***

#### `pick_up(self, object_id: int, bounds: Bounds) -> (List[dict], Arm)`

Begin to try to pick up an object,
Get an IK solution to a target position.

| Parameter | Description |
| --- | --- |
| object_id | The ID of the target object. |
| bounds | Bounds output data. |

_Returns:_  A list of commands to begin bending the arm and the arm doing the pick-up action.

***

#### `on_frame(self, resp: List[bytes]) -> List[dict]`

Update the avatar based on its current arm-bending goals and its state.
If the avatar has achieved a goal (for example, picking up an object), it will stop moving that arm.

| Parameter | Description |
| --- | --- |
| resp | The response from the build. |

_Returns:_  A list of commands to pick up, stop moving, etc.

***

#### `is_ik_done(self) -> bool`

_Returns:_  True if the IK goals are complete, False if the arms are still moving/trying to pick up/etc.

***

#### `put_down(self, reset_arms: bool = True) -> List[dict]`

Put down the object.

| Parameter | Description |
| --- | --- |
| reset_arms | If True, reset arm positions to "neutral". |

_Returns:_  A list of commands to put down the object.

***

#### `reset_arms(self) -> List[dict]`

_Returns:_  A list of commands to drop arms to their starting positions.

***

#### `set_dummy_ik_goals(self) -> None`

Set "dummy" IK goals.
There's no target, so the avatar will just bend the arms until they stop moving.

***

#### `is_holding(self, object_id: int) -> (bool, Arm)`


| Parameter | Description |
| --- | --- |
| object_id | The ID of the object. |

_Returns:_  True if the avatar is holding the object and, if so, the arm holding the object.

***

