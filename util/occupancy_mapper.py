from typing import List, Tuple
import numpy as np
from tdw.floorplan_controller import FloorplanController
from tdw.output_data import Raycast
from sticky_mitten_avatar.util import OCCUPANCY_MAP_DIRECTORY
from sticky_mitten_avatar.environments import Environments


"""
Create an occupancy_maps map of each floorplan and layout by loading in the layout and spherecasting down in a grid.
Save the results to a file.
"""

if __name__ == "__main__":
    c = FloorplanController()
    # This is the minimum size of a surface.
    r = 0.25

    # Iterate through each scene and layout.
    for scene in ["1", "2", "4", "5"]:
        for layout in [0, 1, 2]:
            positions: List[Tuple[float, float, bool]] = []
            # Load the scene and layout.
            commands = c.get_scene_init_commands(scene=scene + "a", layout=layout, audio=False)
            # Get the locations and sizes of each room.
            commands.extend([{"$type": "set_floorplan_roof",
                              "show": False},
                             {"$type": "remove_position_markers"},
                             {"$type": "send_environments"}])
            resp = c.communicate(commands)
            env = Environments(resp=resp)
            # Spherecast to each point.
            x = env.x_min
            while x < env.x_max:
                z = env.z_min
                while z < env.z_max:
                    # Spherecast at the "cell".
                    resp = c.communicate({"$type": "send_spherecast",
                                          "origin": {"x": x, "y": 10, "z": z},
                                          "destination": {"x": x, "y": 0, "z": z},
                                          "radius": r})
                    # Get the y values of each position in the spherecast.
                    ys = []
                    hits = []
                    for j in range(len(resp) - 1):
                        raycast = Raycast(resp[j])
                        ys.append(raycast.get_point()[1])
                        hits.append(raycast.get_hit())
                    # Only include positions in the environment.
                    if len(ys) > 0 and len(hits) > 0 and any([h for h in hits if h]):
                        y = max(ys)
                        # This space is occupied if:
                        # 1. There is a high variance between y values (implying a non-flat surface).
                        # 2. The surface is very low (implying a floor).
                        occupied = np.var(np.array(ys)) > 0.1 or y > 0.01
                        positions.append((x, z, occupied))

                        if not occupied:
                            c.communicate({"$type": "add_position_marker",
                                           "position": {"x": x, "y": 0, "z": z}})
                    z += r
                x += r
                # Save the numpy data.
            np.save(str(OCCUPANCY_MAP_DIRECTORY.joinpath(f"{scene}_{layout}").resolve()),
                    np.array(positions, dtype="f, f, ?"))
            print(scene, layout)
    c.communicate({"$type": "terminate"})
