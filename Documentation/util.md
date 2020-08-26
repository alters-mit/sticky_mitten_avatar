# `sticky_mitten_avatar/util.py`

#### `get_data(resp: List[bytes], d_type: Type[T]) -> Optional[T]`

Parse the output data list of byte arrays to get a single type output data object.

| Parameter | Description |
| --- | --- |
| resp | The response from the build (a list of byte arrays). |
| d_type | The desired type of output data. |

_Returns:_  An object of type `d_type` from `resp`. If there is no object, returns None.

***

#### `get_bounds_dict(bounds: Bounds, index: int) -> Dict[str, np.array]`


| Parameter | Description |
| --- | --- |
| bounds | Bounds output data. |
| index | The index in `bounds` of the target object. |

_Returns:_  A dictionary of the bounds. Key = the name of the position. Value = the position as a numpy array.

***

#### `get_closest_point_in_bounds(origin: np.array, bounds: Bounds, index: int) -> np.array`


| Parameter | Description |
| --- | --- |
| origin | The origin from which the distance is calculated. |
| bounds | Bounds output data. |
| index | The index in `bounds` of the target object. |

_Returns:_  The point on the object bounds closests to `origin`.

***

#### `get_angle(forward: np.array, origin: np.array, position: np.array) -> float`


| Parameter | Description |
| --- | --- |
| position | The target position. |
| origin | The origin position of the directional vector. |
| forward | The forward directional vector. |

_Returns:_  The angle in degrees between `forward` and the direction vector from `origin` to `position`.

***

#### `get_angle_between(v1: np.array, v2: np.array) -> float`


| Parameter | Description |
| --- | --- |
| v1 | The first directional vector. |
| v2 | The second directional vector. |

_Returns:_  The angle in degrees between two directional vectors.

***

#### `rotate_point_around(point: np.array, angle: float, origin: np.array = None) -> np.array`

Rotate a point counterclockwise by a given angle around a given origin.

| Parameter | Description |
| --- | --- |
| origin | The origin position. |
| point | The point being rotated. |
| angle | The angle in degrees. |

***

