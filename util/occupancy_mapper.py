from typing import List, Dict
import numpy as np
from json import dumps
from tdw.floorplan_controller import FloorplanController
from tdw.output_data import Raycast, Version
from sticky_mitten_avatar.util import OCCUPANCY_MAP_DIRECTORY, SCENE_BOUNDS_PATH, OCCUPANCY_CELL_SIZE,\
    Y_MAP_DIRECTORY, get_data
from sticky_mitten_avatar.environments import Environments


"""
Create an occupancy_maps map of each floorplan and layout by loading in the layout and spherecasting down in a grid.
Save the results to a file.
"""


if __name__ == "__main__":
    c = FloorplanController()
    # This is the minimum size of a surface.

    bounds: Dict[str, Dict[str, float]] = dict()

    # Iterate through each scene and layout.
    for scene in ["1", "2", "4", "5"]:
        for layout in [0, 1, 2]:
            positions: List[List[int]] = list()
            y_values: List[List[float]] = list()
            # Load the scene and layout.
            commands = c.get_scene_init_commands(scene=scene + "a", layout=layout, audio=False)
            # Get the locations and sizes of each room.
            commands.extend([{"$type": "set_floorplan_roof",
                              "show": False},
                             {"$type": "remove_position_markers"},
                             {"$type": "send_environments"},
                             {"$type": "send_version"}])
            resp = c.communicate(commands)
            env = Environments(resp=resp)
            is_standalone = get_data(resp=resp, d_type=Version).get_standalone()

            # Cache the environment data.
            if scene not in bounds:
                bounds[scene] = {"x_min": env.x_min,
                                 "x_max": env.x_max,
                                 "z_min": env.z_min,
                                 "z_max": env.z_max}
            # Spherecast to each point.
            x = env.x_min
            while x < env.x_max:
                z = env.z_min
                pos_row: List[int] = list()
                ys_row: List[float] = list()
                while z < env.z_max:
                    # Spherecast at the "cell".
                    resp = c.communicate({"$type": "send_spherecast",
                                          "origin": {"x": x, "y": 10, "z": z},
                                          "destination": {"x": x, "y": 0, "z": z},
                                          "radius": OCCUPANCY_CELL_SIZE})
                    # Get the y values of each position in the spherecast.
                    ys = []
                    hits = []
                    for j in range(len(resp) - 1):
                        raycast = Raycast(resp[j])
                        ys.append(raycast.get_point()[1])
                        hits.append(raycast.get_hit())
                    # This position is outside the environment.
                    if len(ys) == 0 or len(hits) == 0 or len([h for h in hits if h]) == 0:
                        occupied = 2
                        y = -1
                    else:
                        y = max(ys)
                        # This space is occupied if:
                        # 1. There is a high variance between y values (implying a non-flat surface).
                        # 2. The surface is very low (implying a floor).
                        if np.var(np.array(ys)) > 0.1 or y > 0.01:
                            occupied = 0
                        # The position is free.
                        else:
                            occupied = 1
                            if not is_standalone:
                                c.communicate({"$type": "add_position_marker",
                                               "position": {"x": x, "y": 0, "z": z}})
                    pos_row.append(occupied)
                    ys_row.append(y)
                    z += OCCUPANCY_CELL_SIZE
                positions.append(pos_row)
                y_values.append(ys_row)
                x += OCCUPANCY_CELL_SIZE
            # Save the numpy data.
            save_filename = f"{scene}_{layout}"
            np.save(str(OCCUPANCY_MAP_DIRECTORY.joinpath(save_filename).resolve()), np.array(positions))
            np.save(str(Y_MAP_DIRECTORY.joinpath(f"{scene}_{layout}").resolve()), np.array(y_values))
            print(scene, layout)
    c.communicate({"$type": "terminate"})
    SCENE_BOUNDS_PATH.write_text(dumps(bounds, indent=2, sort_keys=True))
