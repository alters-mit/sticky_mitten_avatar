# StaticObjectInfo

`from sticky_mitten_avatar.sticky_mitten_avatar.static_object_info import StaticObjectInfo`

Info for an object that doesn't change between frames, such as its ID and mass.

```python
from sticky_mitten_avatar import StickyMittenAvatarController

c = StickyMittenAvatarController(launch_build=False)
c.init_scene(scene="2a", layout=1, room=1)

# Print each object ID and segmentation color.
for object_id in c.static_object_info:
    object_info = c.static_object_info(object_id)
    print(object_id, object_info.segmentation_color)
```

***

## Static Fields

- `CONTAINERS` The names of every possible container object.

```python
from sticky_mitten_avatar.static_object_info import StaticObjectInfo

# Print the name of each container.
for container in StaticObjectInfo.CONTAINERS:
    print(container)
```

***

## Fields

- `object_id`: The unique ID of the object.
- `mass`: The mass of the object.
- `segmentation_color`: The RGB segmentation color for the object as a numpy array: `[r, g, b]`
- `model_name`: [The name of the model.](https://github.com/threedworld-mit/tdw/blob/master/Documentation/python/librarian/model_librarian.md)
- `category`: The semantic category of the object.
- `container`': If True, this object is container-shaped (a bowl or open basket that smaller objects can be placed in).
- `kinematic`: If True, this object is kinematic, and won't respond to physics. Example: a painting hung on a wall.
- `target_object`: If True, this is a small object that the avatar can place in a container.
- `size`: The size of the object as a numpy array: `[width, height, length]`

***

## Functions

***

#### \_\_init\_\_

**`def __init__(self, object_id: int, rigidbodies: Rigidbodies, segmentation_colors: SegmentationColors, bounds: Bounds, audio: ObjectInfo, target_object: bool = False)`**

| Parameter | Description |
| --- | --- |
| object_id | The unique ID of the object. |
| rigidbodies | Rigidbodies output data. |
| bounds | Bounds output data. |
| segmentation_colors | Segmentation colors output data. |

