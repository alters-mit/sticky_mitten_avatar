import numpy as np
from tdw.output_data import Transforms, Rigidbodies


class DynamicObjectInfo:
    """
    Dynamic physics info (position, velocity, etc.) for a single object.
    Contains the following information as numpy arrays:

    - `position`
    - `forward`
    - `rotation`
    - `velocity`
    - `angular_velocity`
    - `sleeping` (boolean)

    This class is used in the StickyMittenAvatarController.
    """

    def __init__(self, o_id: int, tran: Transforms, rigi: Rigidbodies, tr_index: int):
        """
        :param o_id: The ID of the object.
        :param tran: Transforms data.
        :param rigi: Rigidbodies data.
        :param tr_index: The index of the object in the Transforms object.
        """

        # Get the index in the Rigidbodies object.
        ri_index = -1
        for i in range(rigi.get_num()):
            if rigi.get_id(i) == o_id:
                ri_index = i
                break

        self.position = np.array(tran.get_position(tr_index))
        self.forward = np.array(tran.get_forward(tr_index))
        self.rotation = np.array(tran.get_rotation(tr_index))
        self.velocity = np.array(rigi.get_velocity(ri_index))
        self.angular_velocity = np.array(rigi.get_angular_velocity(ri_index))
        self.sleeping = rigi.get_sleeping(ri_index)
