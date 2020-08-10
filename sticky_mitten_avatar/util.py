import numpy as np
from typing import Dict, List, TypeVar, Type, Tuple
from tdw.output_data import OutputData, AvatarStickyMitten, AvatarStickyMittenSegmentationColors, Transforms,\
    Rigidbodies, Bounds


T = TypeVar("T", bound=OutputData)
# Output data types mapped to their IDs.
_OUTPUT_IDS: Dict[Type[OutputData], str] = {AvatarStickyMittenSegmentationColors: "smsc",
                                            AvatarStickyMitten: "avsm",
                                            Transforms: "tran",
                                            Rigidbodies: "rigi",
                                            Bounds: "boun"}


def get_data(resp: List[bytes], d_type: Type[T]) -> T:
    """
    Parse the output data list of byte arrays to get a single type output data object.

    :param resp: The response from the build (a list of byte arrays).
    :param d_type: The desired type of output data.

    :return: A list of all objects of type `o_type`.
    """

    if d_type not in _OUTPUT_IDS:
        raise Exception(f"Output data ID not defined: {d_type}")

    for i in range(len(resp) - 1):
        r_id = OutputData.get_data_type_id(resp[i])
        if r_id == _OUTPUT_IDS[d_type]:
            return d_type(resp[i])


def get_object_indices(o_id: int, resp: List[bytes]) -> Tuple[int, int]:
    """
    :param o_id: The ID of the object.
    :param resp: The response from the build.
    :return: The indices of the object in the Transforms and Rigidbodies object (in that order). -1 if not found.
    """

    tr = -1
    ri = -1
    tran = get_data(resp=resp, d_type=Transforms)
    rigi = get_data(resp=resp, d_type=Rigidbodies)

    for i in range(tran.get_num()):
        if tran.get_id(i) == o_id:
            tr = i
            break
    for i in range(rigi.get_num()):
        if rigi.get_id(i) == o_id:
            ri = i
            break
    return tr, ri


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
