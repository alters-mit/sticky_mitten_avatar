import numpy as np
from typing import Dict, List, TypeVar, Type, Optional
from tdw.output_data import OutputData, Transforms, Rigidbodies, Bounds, Images, SegmentationColors, Volumes, Raycast, \
    CompositeObjects, CameraMatrices, Environments, Overlap, Version, NavMeshPath


# The size of each occupancy grid cell.
OCCUPANCY_CELL_SIZE = 0.25

T = TypeVar("T", bound=OutputData)
# Output data types mapped to their IDs.
_OUTPUT_IDS: Dict[Type[OutputData], str] = {Transforms: "tran",
                                            Rigidbodies: "rigi",
                                            Bounds: "boun",
                                            Images: "imag",
                                            SegmentationColors: "segm",
                                            Volumes: "volu",
                                            Raycast: "rayc",
                                            CompositeObjects: "comp",
                                            CameraMatrices: "cama",
                                            Environments: "envi",
                                            Overlap: "over",
                                            Version: "vers",
                                            NavMeshPath: "path"}
# Global forward directional vector.
FORWARD = np.array([0, 0, 1])
# The mass of a target object.
TARGET_OBJECT_MASS = 0.25
# The mass of a container.
CONTAINER_MASS = 1
# The scale of every container.
CONTAINER_SCALE = {"x": 0.6, "y": 0.4, "z": 0.6}


def get_data(resp: List[bytes], d_type: Type[T]) -> Optional[T]:
    """
    Parse the output data list of byte arrays to get a single type output data object.

    :param resp: The response from the build (a byte array).
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
