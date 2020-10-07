from typing import Dict, List
from tdw.controller import Controller
from tdw.tdw_utils import TDWUtils, QuaternionUtils
from tdw.output_data import OutputData, Collision, EnvironmentCollision, Rigidbodies
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
    stays: List[Collision] = list()
    while not sleeping:
        resp = c.communicate([])
        rigidbodies = get_data(resp=resp, d_type=Rigidbodies)
        o_sleep = False
        p_sleep = False
        for i in range(rigidbodies.get_num()):
            if rigidbodies.get_id(i) == o_id:
                o_sleep = rigidbodies.get_sleeping(i)
                collisions, env_collisions = get_collisions(resp=resp)
                if not o_sleep:
                    stays.clear()
                    collisions, env_collisions = get_collisions(resp=resp)
                    for coll in collisions:
                        if coll.get_state() == "stay" and (coll.get_collider_id() == o_id or coll.get_collidee_id() == o_id):
                            stays.append(coll)
            elif rigidbodies.get_id(i) == p_id:
                p_sleep = rigidbodies.get_sleeping(i)
        sleeping = o_sleep and p_sleep

    assert len(stays) > 0
    coll = stays[0]
    assert coll.get_state() == "stay"
    assert coll.get_collidee_id() == o_id or coll.get_collider_id() == o_id
    assert coll.get_collidee_id() == basket_id or coll.get_collider_id() == basket_id
    for i in range(coll.get_num_contacts()):
        assert coll.get_contact_normal(i)[1] > 0
