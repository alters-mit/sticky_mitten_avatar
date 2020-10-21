# `body_part_static.py`

## `BodyPartStatic`

`from tdw.sticky_mitten_avatar.body_part_static import BodyPartStatic`

Static data for a body part in an avatar.

Fields:

- `object_id` The object ID of the body part.
- `segmentation_color` The segmentation color of the body part.
- `name` The name of the body part.
- `audio` [Audio values](https://github.com/threedworld-mit/tdw/blob/master/Documentation/python/py_impact.md#objectinfo) for the body part.

***

#### \_\_init\_\_

**`def __init__(self, object_id: int, segmentation_color: Tuple[float, float, float], name: str, mass: float)`**


| Parameter | Description |
| --- | --- |
| object_id | The object ID of the body part. |
| segmentation_color | The segmentation color of the body part. |
| name | The name of the body part. |
| mass | The mass of the body part. |

***

