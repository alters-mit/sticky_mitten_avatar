from pathlib import Path
import json
from tdw.controller import Controller
from tdw.tdw_utils import TDWUtils
from tdw.output_data import CompositeObjects

"""
Get default audio data for each sub-object of a composite object.
"""


if __name__ == "__main__":
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("--model", default="puzzle_box_composite")
    args = parser.parse_args()

    c = Controller()
    c.start()
    resp = c.communicate([TDWUtils.create_empty_room(12, 12),
                          c.get_add_object(model_name=args.model, object_id=0),
                          {"$type": "send_composite_objects"}])
    c.communicate({"$type": "terminate"})

    # Parse the composite object data.
    co = CompositeObjects(resp[0])
    sub_objects = dict()
    for i in range(co.get_num()):
        object_id = co.get_object_id(i)
        for j in range(co.get_num_sub_objects(i)):
            machine = co.get_sub_object_machine_type(i, j)
            name = co.get_sub_object_name(i, j)
            sub_objects[name] = {"amp": 0,
                                 "mass": 0,
                                 "material": "wood",
                                 "bounciness": 0,
                                 "library": "",
                                 "machine": machine}
    root = {"amp": 0,
            "bounciness": 0,
            "library": "",
            "machine": "none",
            "mass": 0,
            "material": "wood"}
    composite_object = {"root": root,
                        "sub_objects": sub_objects}
    # Add the data.
    p = Path("sticky_mitten_avatar/composite_object_audio.json")
    data = json.loads(p.read_text(encoding="utf-8"))
    data[args.model] = composite_object
    p.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

