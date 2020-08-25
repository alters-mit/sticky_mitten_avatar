# `sticky_mitten_avatar/static_object_info.py`

## `StaticObjectInfo`

`from tdw.sticky_mitten_avatar.static_object_info import StaticObjectInfo`

Info for an object that doesn't change between frames.

Fields:

- `object_id`: The unique ID of the object.
- `mass`: The mass of the object.
- `segmentation_color`: The RGB segmentation color.
- `model_name`: The name of the object's [model](https://github.com/threedworld-mit/tdw/blob/master/Documentation/python/librarian/model_librarian.md)
- `volume`: The "naive" volume: length * width * height, assuming the object was brick-shaped.
- `hollowness`: The percentage (between 0 and 1) of the object's volume that is empty space.

***

#### `__init__(self, index: int, rigidbodies: Rigidbodies, segmentation_colors: SegmentationColors, bounds: Bounds, volumes: Volumes)`


| Parameter | Description |
| --- | --- |
| index | The index of the object in `segmentation_colors` |
| rigidbodies | Rigidbodies output data. |
| segmentation_colors | Segmentation colors output data. |
| bounds | Bounds output data. |
| volumes | Volumes output data. |

***

