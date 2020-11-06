# BodyPartStatic

`from sticky_mitten_avatar.sticky_mitten_avatar.body_part_static import BodyPartStatic`

Static data for a body part in an avatar, such as a torso, an elbow, etc.

```python
from sticky_mitten_avatar import StickyMittenAvatarController

c = StickyMittenAvatarController(launch_build=False)
c.init_scene(scene="2a", layout=1, room=1)

# Print each body part ID and segmentation color.
for body_part_id in c.static_avatar_data:
    body_part = c.static_avatar_data[body_part_id]
    print(body_part_id, body_part.segmentation_color)
```

***

## Fields

- `object_id` The object ID of the body part.
- `segmentation_color` The segmentation color of the body part as a numpy array: `[r, g, b]`.
- `name` The name of the body part.
- `mass` The mass of the body part.

***

## Functions

***

#### \_\_init\_\_

**`def __init__(self, object_id: int, segmentation_color: Tuple[float, float, float], name: str, mass: float)`**

| Parameter | Description |
| --- | --- |
| object_id | The object ID of the body part. |
| segmentation_color | The segmentation color of the body part. |
| name | The name of the body part. |
| mass | The mass of the body part. |

