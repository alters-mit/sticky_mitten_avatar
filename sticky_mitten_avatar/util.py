import numpy as np
from typing import Dict, List, TypeVar, Type, Optional
from tdw.output_data import OutputData, Transforms, Rigidbodies, Bounds, Images, SegmentationColors, Volumes, Raycast


T = TypeVar("T", bound=OutputData)
# Output data types mapped to their IDs.
_OUTPUT_IDS: Dict[Type[OutputData], str] = {Transforms: "tran",
                                            Rigidbodies: "rigi",
                                            Bounds: "boun",
                                            Images: "imag",
                                            SegmentationColors: "segm",
                                            Volumes: "volu",
                                            Raycast: "rayc"}
# Global forward directional vector.
FORWARD = np.array([0, 0, 1])


def get_data(resp: List[bytes], d_type: Type[T]) -> Optional[T]:
    """
    Parse the output data list of byte arrays to get a single type output data object.

    :param resp: The response from the build (a list of byte arrays).
    :param d_type: The desired type of output data.

    :return: An object of type `d_type` from `resp`. If there is no object, returns None.
    """

    if d_type not in _OUTPUT_IDS:
        raise Exception(f"Output data ID not defined: {d_type}")

    for i in range(len(resp) - 1):
        r_id = OutputData.get_data_type_id(resp[i])
        if r_id == _OUTPUT_IDS[d_type]:
            return d_type(resp[i])
    return None


def get_bounds_dict(bounds: Bounds, index: int) -> Dict[str, np.array]:
    """
    :param bounds: Bounds output data.
    :param index: The index in `bounds` of the target object.

    :return: A dictionary of the bounds. Key = the name of the position. Value = the position as a numpy array.
    """

    return {"top": np.array(bounds.get_top(index)),
            "bottom": np.array(bounds.get_bottom(index)),
            "left": np.array(bounds.get_left(index)),
            "right": np.array(bounds.get_right(index)),
            "front": np.array(bounds.get_front(index)),
            "back": np.array(bounds.get_back(index))}


def get_closest_point_in_bounds(origin: np.array, bounds: Bounds, index: int) -> np.array:
    """
    :param origin: The origin from which the distance is calculated.
    :param bounds: Bounds output data.
    :param index: The index in `bounds` of the target object.

    :return: The point on the object bounds closests to `origin`.
    """

    object_bounds = get_bounds_dict(bounds=bounds, index=index)

    # Get the closest point on the bounds.
    min_destination = ""
    min_distance = 10000
    for p in object_bounds:
        d = np.linalg.norm(origin - object_bounds[p])
        if d < min_distance:
            min_distance = d
            min_destination = p
    return object_bounds[min_destination]


def get_angle(forward: np.array, origin: np.array, position: np.array) -> float:
    """
      :param position: The target position.
      :param origin: The origin position of the directional vector.
      :param forward: The forward directional vector.

      :return: The angle in degrees between `forward` and the direction vector from `origin` to `position`.
      """

    # Get the normalized directional vector to the target position.
    d = position - origin
    d = d / np.linalg.norm(d)

    ang1 = np.arctan2(forward[2], forward[0])
    ang2 = np.arctan2(d[2], d[0])

    return np.rad2deg((ang1 - ang2) % (2 * np.pi))


def get_angle_between(v1: np.array, v2: np.array) -> float:
    """
    :param v1: The first directional vector.
    :param v2: The second directional vector.

    :return: The angle in degrees between two directional vectors.
    """

    ang1 = np.arctan2(v1[2], v1[0])
    ang2 = np.arctan2(v2[2], v2[0])

    return np.rad2deg((ang1 - ang2) % (2 * np.pi))


def rotate_point_around(point: np.array, angle: float, origin: np.array = None) -> np.array:
    """
    Rotate a point counterclockwise by a given angle around a given origin.

    :param origin: The origin position.
    :param point: The point being rotated.
    :param angle: The angle in degrees.
    """

    if origin is None:
        origin = np.array([0, 0, 0])

    radians = np.deg2rad(angle)
    x, y = point[0], point[2]
    offset_x, offset_y = origin[0], origin[2]
    adjusted_x = (x - offset_x)
    adjusted_y = (y - offset_y)
    cos_rad = np.cos(radians)
    sin_rad = np.sin(radians)
    qx = offset_x + cos_rad * adjusted_x + sin_rad * adjusted_y
    qy = offset_y + -sin_rad * adjusted_x + cos_rad * adjusted_y

    return np.array([qx, point[1], qy])
