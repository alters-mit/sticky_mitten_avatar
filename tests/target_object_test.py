from pathlib import Path
from tdw.controller import Controller
from tdw.tdw_utils import TDWUtils

"""
Test the scale of target objects.
"""

if __name__ == "__main__":
    txt = Path("../sticky_mitten_avatar/object_data/target_objects.csv").read_text(encoding="utf-8")
    c = Controller(launch_build=False)
    c.start()
    commands = [TDWUtils.create_empty_room(12, 12)]
    y = 0
    o_id = 0
    for line in txt.split("\n")[1:]:
        line_split = line.split(",")
        model = line_split[0]
        scale = float(line_split[1])
        commands.extend([c.get_add_object(model_name=model, object_id=o_id, position={"x": 0, "y": y, "z": 0}),
                         {"$type": "scale_object",
                          "scale_factor": {"x": scale, "y": scale, "z": scale},
                          "id": o_id}])
        o_id += 1
        y += scale / 2
    c.communicate(commands)
