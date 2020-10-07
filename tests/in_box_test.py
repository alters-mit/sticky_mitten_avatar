from tdw.controller import Controller
from tdw.tdw_utils import TDWUtils, QuaternionUtils
from tdw.output_data import OutputData, Collision, EnvironmentCollision, Rigidbodies, OverlapSphere
from sticky_mitten_avatar.util import get_data, get_collisions


if __name__ == "__main__":
    basket_id = 0
    o_id = 1
    p_id = 2
    c = Controller(launch_build=False)
    c.start()
    resp = c.communicate([TDWUtils.create_empty_room(12, 12),
                          c.get_add_object("basket_18inx18inx12iin", object_id=basket_id),
                          c.get_add_object("pepper", object_id=o_id, position={"x": 0, "y": 0.08, "z": 0}),
                          c.get_add_object("pepper", object_id=p_id, position={"x": 0, "y": 0.22, "z": 0.24}),
                          {"$type": "set_sleep_threshold",
                           "sleep_threshold": 0.1},
                          {"$type": "send_rigidbodies",
                           "frequency": "always"}])
    sleeping = False
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
    resp = c.communicate({"$type": "send_overlap_sphere",
                          "position": {"x": 0, "y": 0, "z": 0},
                          "radius": 0.19})
    sphere = get_data(resp=resp, d_type=OverlapSphere)
    sphere_ids = sphere.get_object_ids()
    assert o_id in sphere_ids
    assert p_id not in sphere_ids
