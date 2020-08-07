from typing import Dict, List, TypeVar, Type
from tdw.output_data import OutputData, AvatarStickyMitten, AvatarStickyMittenSegmentationColors, Transforms


T = TypeVar("T", bound=OutputData)
# Output data types mapped to their IDs.
_OUTPUT_IDS: Dict[Type[OutputData], str] = {AvatarStickyMittenSegmentationColors: "smsc",
                                            AvatarStickyMitten: "avsm",
                                            Transforms: "tran"}


def get_data(resp: List[bytes], o_type: Type[T]) -> T:
    """
    Parse the output data list of byte arrays to get a single type output data object.

    :param resp: The response from the build (a list of byte arrays).
    :param o_type: The desired type of output data.

    :return: A list of all objects of type `o_type`.
    """

    if o_type not in _OUTPUT_IDS:
        raise Exception(f"Output data ID not defined: {o_type}")

    for i in range(len(resp) - 1):
        r_id = OutputData.get_data_type_id(resp[i])
        if r_id == _OUTPUT_IDS[o_type]:
            return o_type(resp[i])
