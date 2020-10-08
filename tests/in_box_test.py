import numpy as np
from typing import Dict, List
from tdw.controller import Controller
from tdw.tdw_utils import TDWUtils, QuaternionUtils
from tdw.output_data import OutputData, Collision, EnvironmentCollision, Rigidbodies, Overlap, Transforms
from sticky_mitten_avatar.util import get_data, get_collisions


if __name__ == "__main__":
    basket_id = 0
    o_id = 1
    p_id = 2
    c = Controller(launch_build=False)
    c.start()
    resp = c.communicate([TDWUtils.create_empty_room(12, 12),
                          c.get_add_object("basket_18inx18inx12iin",
                                           object_id=basket_id),
                          c.get_add_object("pepper", object_id=o_id,
                                           position={"x": 0, "y": 0.08, "z": 0},
                                           rotation={"x": 60, "y": -70, "z": 5}),
                          c.get_add_object("pepper", object_id=p_id,
                                           position={"x": 0, "y": 0.22, "z": 0.24}),
                          {"$type": "set_sleep_threshold",
                           "sleep_threshold": 0.1},
                          {"$type": "send_rigidbodies",
                           "frequency": "always"},
                          {"$type": "send_collisions",
                           "enter": True,
                           "stay": True,
                           "exit": True}])
    sleeping = False
    # Iterate until the objects are sleeping.
    while not sleeping:
        resp = c.communicate([])
        rigidbodies = get_data(resp=resp, d_type=Rigidbodies)
        o_sleep = False
        p_sleep = False
        for i in range(rigidbodies.get_num()):
            if rigidbodies.get_id(i) == o_id:
                o_sleep = rigidbodies.get_sleeping(i)
            elif rigidbodies.get_id(i) == p_id:
                p_sleep = rigidbodies.get_sleeping(i)
        sleeping = o_sleep and p_sleep

    resp = c.communicate({"$type": "send_transforms",
                          "frequency": "once",
                          "ids": [basket_id]})
    tr = get_data(resp=resp, d_type=Transforms)

    # Cast a box.
    rot = tr.get_rotation(0)
    up = QuaternionUtils.get_up_direction(rot)
    center = np.array(tr.get_position(0)) + (up * 0.2)
    resp = c.communicate({"$type": "send_overlap_box",
                          "position": TDWUtils.array_to_vector3(center),
                          "half_extents": {"x": 0.2, "y": 0.2, "z": 0.2},
                          "rotation": TDWUtils.array_to_vector4(rot)})
    overlap = get_data(resp=resp, d_type=Overlap)
    overlap_ids = overlap.get_object_ids()
    assert o_id in overlap_ids
    assert basket_id in overlap_ids
    assert p_id not in overlap_ids
