from typing import List, Tuple
import numpy as np
from tdw.floorplan_controller import FloorplanController
from tdw.output_data import Environments, Raycast
from sticky_mitten_avatar.util import OCCUPANCY_MAP_DIRECTORY


"""
Create an occupancy map of each floorpland and layout.
"""

if __name__ == "__main__":
    c = FloorplanController()
    # This is the minimum size of a surface.
    r = 0.5
    for scene in ["1", "2", "4", "5"]:
        for layout in [0, 1, 2]:
            positions: List[Tuple[float, float, bool]] = []
            # Load the scene and layout.
            commands = c.get_scene_init_commands(scene=scene + "a", layout=layout, audio=False)
            # Get the locations and sizes of each room.
            commands.extend([{"$type": "set_floorplan_roof",
                              "show": False},
                             {"$type": "send_environments"}])
            resp = c.communicate(commands)
            env = Environments(resp[0])

            # Get the overall size of the scene.
            x_min = 1000
            x_max = 0
            z_min = 1000
            z_max = 0
            for i in range(env.get_num()):
                center = env.get_center(i)
                bounds = env.get_bounds(i)
                x_0 = center[0] - (bounds[0] / 2)
                if x_0 < x_min:
                    x_min = x_0
                z_0 = center[2] - (bounds[2] / 2)
                if z_0 < z_min:
                    z_min = z_0
                x_1 = center[0] + (bounds[0] / 2)
                if x_1 > x_max:
                    x_max = x_1
                z_1 = center[2] + (bounds[2] / 2)
                if z_1 > z_max:
                    z_max = z_1
            # Spherecast to each point.
            x = x_min
            while x <= x_max:
                z = z_min
                while z <= z_max:
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

                        if occupied:
                            c.communicate({"$type": "add_position_marker",
                                           "position": {"x": x, "y": 0, "z": z}})
                    z += r
                x += r
                # Save the numpy data.
            np.save(str(OCCUPANCY_MAP_DIRECTORY.joinpath(f"{scene}_{layout}").resolve()),
                    np.array(positions, dtype="f, f, ?"))
            print(scene, layout)
    c.communicate({"$type": "terminate"})
