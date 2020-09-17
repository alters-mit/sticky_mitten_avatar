# `static_object_info.py`

## `StaticObjectInfo`

`from tdw.sticky_mitten_avatar.static_object_info import StaticObjectInfo`

Info for an object that doesn't change between frames.

Fields:

- `object_id`: The unique ID of the object.
- `mass`: The mass of the object.
- `segmentation_color`: The RGB segmentation color for the object as a numpy array.
- `model_name`: [The name of the model.](https://github.com/threedworld-mit/tdw/blob/master/Documentation/python/librarian/model_librarian.md)
- `audio`: [Audio properties.](https://github.com/threedworld-mit/tdw/blob/master/Documentation/python/py_impact.md#objectinfo)

***

#### \_\_init\_\_

**`def __init__(self, index: int, rigidbodies: Rigidbodies, segmentation_colors: SegmentationColors, audio: ObjectInfo)`**


| Parameter | Description |
| --- | --- |
| index | The index of the object in `segmentation_colors` |
| rigidbodies | Rigidbodies output data. |
| segmentation_colors | Segmentation colors output data. |

***

