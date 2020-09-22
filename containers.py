from json import dumps
from pathlib import Path
from tdw.controller import Controller
from tdw.tdw_utils import TDWUtils
from tdw.output_data import Raycast


"""
Get the dimensions of a container without a lid (e.g. a basket) by adding the object and raycasting down.
Record these values in a json file.
"""


if __name__ == "__main__":
    model_names = ['basket_18inx18inx12iin', 'basket_18inx18inx12iin_bamboo', 'basket_18inx18inx12iin_plastic_lattice',
                   'basket_18inx18inx12iin_wicker', 'basket_18inx18inx12iin_wood_mesh', 'box_18inx18inx12in_cardboard',
                   'box_24inx18inx12in_cherry', 'box_tapered_beech', 'box_tapered_white_mesh',
                   'round_bowl_large_metal_perf', 'round_bowl_large_padauk', 'round_bowl_large_thin',
                   'round_bowl_small_beech', 'round_bowl_small_walnut', 'round_bowl_talll_wenge',
                   'shallow_basket_white_mesh', 'shallow_basket_wicker']

    c = Controller()
    c.start()
    c.communicate(TDWUtils.create_empty_room(12, 12))

    container_dimensions = dict()

    for model_name in model_names:
        # Add the object and raycast down to it.
        resp = c.communicate([c.get_add_object(model_name=model_name, object_id=0),
                              {"$type": "send_raycast",
                               "origin": {"x": 0, "y": 100, "z": 0},
                               "destination": {"x": 0, "y": 0, "z": 0}}])
        raycast = Raycast(resp[0])
        # Get the y value of the base.
        y = raycast.get_point()[1]
        # Move the raycast slightly through many iterations to get an approximate radius.
        done_raycasting = False
        radius = 0
        d_x = 0.02
        x = d_x
        while not done_raycasting:
            resp = c.communicate([{"$type": "send_raycast",
                                   "origin": {"x": x, "y": 100, "z": 0},
                                   "destination": {"x": x, "y": 0, "z": 0}}])
            raycast = Raycast(resp[0])
            # If the raycast didn't hit, we got the approximate radius.
            if raycast.get_point()[1] < y:
                done_raycasting = True
                container_dimensions[model_name] = {"y": y, "r": x * 0.9}
            # Move the raycast.
            x += d_x
        c.communicate({"$type": "destroy_all_objects"})
        print(model_name)
    c.communicate({"$type": "terminate"})

    # Add shoebox_fused.
    container_dimensions["shoebox_fused"] = {"y": 0.01, "r": 0.07225619999999999}

    # Write to disk.
    Path("sticky_mitten_avatar/container_dimensions.json").write_text(dumps(container_dimensions, indent=2,
                                                                            sort_keys=True))
    print("Done!")
