from typing import List, Dict
import numpy as np
from json import dumps
from tdw.floorplan_controller import FloorplanController
from tdw.output_data import Raycast, Version
from tdw.tdw_utils import TDWUtils
from sticky_mitten_avatar.util import OCCUPANCY_CELL_SIZE, get_data
from sticky_mitten_avatar.paths import OCCUPANCY_MAP_DIRECTORY, SCENE_BOUNDS_PATH, Y_MAP_DIRECTORY, \
    SURFACE_MAP_DIRECTORY
from sticky_mitten_avatar.environments import Environments


"""
Create an occupancy_maps map of each floorplan and layout by loading in the layout and spherecasting down in a grid.
Save the results to a file.
"""


if __name__ == "__main__":
    c = FloorplanController(launch_build=False)
    # This is the minimum size of a surface.

    bounds: Dict[str, Dict[str, float]] = dict()

    # Iterate through each scene and layout.
    for scene in ["1", "2", "4", "5"]:
        for layout in [0, 1, 2]:
            positions = list()
            y_values = list()
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
                    surface = False
                    origin = {"x": x, "y": 3.5, "z": z}
                    destination = {"x": x, "y": -1, "z": z}
                    # Spherecast at the "cell".
                    resp = c.communicate({"$type": "send_spherecast",
                                          "origin": origin,
                                          "destination": destination,
                                          "radius": OCCUPANCY_CELL_SIZE})
                    # Get the y values of each position in the spherecast.
                    ys = []
                    hits = []
                    hit_objs = []
                    for j in range(len(resp) - 1):
                        raycast = Raycast(resp[j])
                        raycast_y = raycast.get_point()[1]
                        is_hit = raycast.get_hit() and (not raycast.get_hit_object() or raycast_y > 0.01)
                        if is_hit:
                            ys.append(raycast_y)
                            hit_objs.append(raycast.get_hit_object())
                        hits.append(is_hit)
                    # This position is outside the environment.
                    if len(ys) == 0 or len(hits) == 0 or len([h for h in hits if h]) == 0 or max(ys) > 2.8:
                        occupied = 2
                        y = -1
                    else:
                        # This space is occupied if:
                        # 1. The spherecast hit any objects.
                        # 2. There is a high variance between y values (implying a non-flat surface).
                        # 3. The surface is very low (implying a floor).
                        if any(hit_objs) and np.var(np.array(ys)) > 0.1 or max(ys) > 0.01:
                            occupied = 0
                            # Raycast to get the y value.
                            resp = c.communicate({"$type": "send_raycast",
                                                  "origin": origin,
                                                  "destination": destination})
                            raycast = Raycast(resp[0])
                            y = raycast.get_point()[1]
                            if raycast.get_hit_object() and 0.01 < y < 0.45 and not is_standalone:
                                c.communicate({"$type": "add_position_marker",
                                               "position": TDWUtils.array_to_vector3(raycast.get_point()),
                                               "color": {"r": 0, "g": 1, "b": 0, "a": 1},
                                               "scale": 0.1})
                        # The position is free.
                        else:
                            y = 0
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

            # Calculate reachable surfaces.
            positions = np.array(positions)
            y_values = np.array(y_values)
            reachable_surfaces = np.zeros(positions.shape, dtype=bool)

            # Calculate reachable surfaces.
            for ix, iy in np.ndindex(positions.shape):
                # Get something low-lying in the scene.
                if positions[ix][iy] == 2 or y_values[ix][iy] > 0.45:
                    continue
                elif positions[ix][iy] == 1:
                    reachable_surfaces[ix][iy] = True
                    continue
                for jx, jy in np.ndindex(positions.shape):
                    if positions[jx][jy] == 1 and np.linalg.norm(np.array([ix, iy]) - np.array([jx, jy])) <= 3:
                        reachable_surfaces[ix][iy] = True
                        break

            # Save the numpy data.
            save_filename = f"{scene}_{layout}"
            np.save(str(OCCUPANCY_MAP_DIRECTORY.joinpath(save_filename).resolve()), positions)
            np.save(str(Y_MAP_DIRECTORY.joinpath(save_filename).resolve()), y_values)
            np.save(str(SURFACE_MAP_DIRECTORY.joinpath(save_filename).resolve()), reachable_surfaces)
            print(scene, layout)
            if not is_standalone:
                c.communicate({"$type": "pause_editor"})
    c.communicate({"$type": "terminate"})
    SCENE_BOUNDS_PATH.write_text(dumps(bounds, indent=2, sort_keys=True))
