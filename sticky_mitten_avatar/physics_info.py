import numpy as np
from typing import List
from tdw.output_data import Transforms, Rigidbodies
from sticky_mitten_avatar.util import get_data, get_object_indices


class PhysicsInfo:
    """
    Dynamic physics info (position, velocity, etc.) for a single object.
    """

    def __init__(self, o_id: int, resp: List[bytes]):
        """
        :param o_id: The ID of the object.
        :param resp: The response from the build.
        """

        tr_id, ri_id = get_object_indices(o_id=o_id, resp=resp)
        tran = get_data(resp=resp, d_type=Transforms)
        rigi = get_data(resp=resp, d_type=Rigidbodies)

        self.position = np.array(tran.get_position(tr_id))
        self.forward = np.array(tran.get_forward(tr_id))
        self.rotation = np.array(tran.get_rotation(tr_id))
        self.velocity = np.array(rigi.get_velocity(ri_id))
        self.angular_velocity = np.array(rigi.get_angular_velocity(ri_id))
        self.sleeping = rigi.get_sleeping(ri_id)
