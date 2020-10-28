from json import loads
from typing import List, Dict, Tuple
import numpy as np
from json import dumps
from tdw.floorplan_controller import FloorplanController
from tdw.output_data import OutputData, Raycast, Version, SegmentationColors, NavMeshPath, IsOnNavMesh
from tdw.tdw_utils import TDWUtils
from tdw.librarian import ModelLibrarian
from sticky_mitten_avatar.util import OCCUPANCY_CELL_SIZE, get_data
from sticky_mitten_avatar.paths import OCCUPANCY_MAP_DIRECTORY, SCENE_BOUNDS_PATH, Y_MAP_DIRECTORY, \
    SURFACE_MAP_DIRECTORY, ROOM_MAP_DIRECTORY, SPAWN_POSITIONS_PATH, SURFACE_OBJECT_CATEGORIES_PATH,\
    OBJECT_SPAWN_MAP_DIRECTORY
from sticky_mitten_avatar.environments import Environments


"""
Create an occupancy_maps map of each floorplan and layout by loading in the layout and spherecasting down in a grid.
Save the results to a file.
"""


if __name__ == "__main__":
    # Valid categories of surface models.
    surface_object_categories = loads(SURFACE_OBJECT_CATEGORIES_PATH.read_text(encoding="utf-8"))
    lib = ModelLibrarian()

    c = FloorplanController(launch_build=False)
    # This is the minimum size of a surface.

    bounds: Dict[str, Dict[str, float]] = dict()

    # Iterate through each scene and layout.
    for scene in ["1", "2", "4", "5"]:
        for layout in [0, 1, 2]:
            spawn_positions = loads(SPAWN_POSITIONS_PATH.read_text())[scene[0]][str(layout)]
            positions = list()
            y_values = list()
            object_ids = list()
            object_spawns = list()
            # Load the scene and layout.
            commands = c.get_scene_init_commands(scene=scene + "a", layout=layout, audio=True)
            # Make all non-kinematic objects NavMesh obstacles.
            carve_commands = []
            for cmd in commands:
                if cmd["$type"] == "set_kinematic_state" and not cmd["is_kinematic"]:
                    carve_commands.append({"$type": "make_nav_mesh_obstacle",
                                           "id": cmd["id"],
                                           "carve_type": "stationary",
                                           "scale": 0.5})
            commands.extend(carve_commands)
            
            # Get the locations and sizes of each room.
            commands.extend([{"$type": "set_floorplan_roof",
                              "show": False},
                             {"$type": "remove_position_markers"},
                             {"$type": "send_environments"},
                             {"$type": "send_version"},
                             {"$type": "send_segmentation_colors"}])
            # Send the commands.
            resp = c.communicate(commands)
            env = Environments(resp=resp)
            is_standalone = get_data(resp=resp, d_type=Version).get_standalone()
            # Cache the names of all objects and get all surface models.
            segmentation_colors = get_data(resp=resp, d_type=SegmentationColors)

            # Ignore spawn positions that aren't on the NavMesh (we know that they are navigable).
            temp_spawn_positions = []
            # Check whether each spawn position is on the NavMesh.
            for spawn_position in spawn_positions:
                resp = c.communicate({"$type": "send_is_on_nav_mesh",
                                      "position": spawn_position,
                                      "max_distance": 0.25})
                for i in range(len(resp) - 1):
                    r_id = OutputData.get_data_type_id(resp[i])
                    if r_id == "isnm":
                        isnm = IsOnNavMesh(resp[i])
                        if isnm.get_is_on():
                            temp_spawn_positions.append(spawn_position)
            spawn_positions = temp_spawn_positions

            object_names: Dict[int, str] = dict()
            surface_ids: List[int] = list()
            for i in range(segmentation_colors.get_num()):
                object_name = segmentation_colors.get_object_name(i).lower()
                object_id = segmentation_colors.get_object_id(i)
                object_names[object_id] = object_name
                record = lib.get_record(object_name)
                # Check if this is a surface.
                # The record might be None if this is a composite object.
                if record is not None and record in surface_object_categories:
                    surface_ids.append(object_id)

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
                ids_row: List[int] = list()
                spawn_row: List[bool] = list()
                while z < env.z_max:
                    object_id = None
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
                        navigable = False
                    else:
                        # This space is occupied if:
                        # 1. The spherecast hit any objects.
                        # 2. The surface is higher than floor level (such that carpets are ignored).
                        if any(hit_objs) and max(ys) > 0.03:
                            occupied = 0
                            navigable = False
                            # Raycast to get the y value.
                            resp = c.communicate({"$type": "send_raycast",
                                                  "origin": origin,
                                                  "destination": destination})
                            raycast = Raycast(resp[0])
                            y = raycast.get_point()[1]
                            hit_object = raycast.get_hit_object()
                            if hit_object:
                                object_id = raycast.get_object_id()
                            if hit_object and 0.03 < y < 0.45 and not is_standalone:
                                c.communicate({"$type": "add_position_marker",
                                               "position": TDWUtils.array_to_vector3(raycast.get_point()),
                                               "color": {"r": 0, "g": 1, "b": 0, "a": 1},
                                               "scale": 0.1})
                        # The position is free.
                        else:
                            y = 0
                            occupied = 1
                            # Is this position navigable from each spawn position?
                            navigable = True
                            for spawn_position in spawn_positions:
                                resp = c.communicate({"$type": "send_nav_mesh_path",
                                                      "origin": spawn_position,
                                                      "destination": {"x": x, "y": y, "z": z}})
                                path = get_data(resp=resp, d_type=NavMeshPath)
                                if path.get_state() != "complete":
                                    navigable = False
                                    break
                            if not is_standalone:
                                c.communicate({"$type": "add_position_marker",
                                               "position": {"x": x, "y": 0, "z": z}})
                    pos_row.append(occupied)
                    ys_row.append(y)
                    ids_row.append(object_id)
                    spawn_row.append(navigable)
                    z += OCCUPANCY_CELL_SIZE
                positions.append(pos_row)
                y_values.append(ys_row)
                object_ids.append(ids_row)
                object_spawns.append(spawn_row)
                x += OCCUPANCY_CELL_SIZE
            positions = np.array(positions)
            y_values = np.array(y_values)
            object_ids = np.array(object_ids)
            object_spawns = np.array(object_spawns)

            # Load the room map.
            room_map = np.load(str(ROOM_MAP_DIRECTORY.joinpath(f"{scene[0]}.npy").resolve()))

            surfaces: Dict[int, Dict[str, List[Tuple[int, int]]]] = dict()

            # Calculate surfaces.
            for ix, iy in np.ndindex(positions.shape):
                # Ignore positions that aren't objects, aren't in the scene, or too high, or not a surface.
                if object_ids[ix][iy] is None or positions[ix][iy] == 2 or y_values[ix][iy] < 0.03 or\
                        y_values[ix][iy] > 0.45 or object_ids[ix][iy] not in surface_ids:
                    continue
                # Get the room that the position is in.
                room = int(room_map[ix][iy])
                # Ignore objects that aren't in a zone that has been demarcated as a room.
                if room < 0:
                    continue
                # Check if the avatar can reach this position.
                reachable = False
                for jx, jy in np.ndindex(positions.shape):
                    if positions[jx][jy] == 1 and np.linalg.norm(np.array([ix, iy]) - np.array([jx, jy])) <= 1.5:
                        reachable = True
                        break
                if reachable:
                    if room not in surfaces:
                        surfaces[room] = dict()
                    # Add the position to the dictionary.
                    object_name = object_names[object_ids[ix][iy]]
                    object_category = surface_object_categories[object_name]
                    if object_category not in surfaces[room]:
                        surfaces[room][object_category] = list()
                    surfaces[room][object_category].append((ix, iy))
            # Save the numpy data.
            save_filename = f"{scene}_{layout}"
            np.save(str(OCCUPANCY_MAP_DIRECTORY.joinpath(save_filename).resolve()), positions)
            np.save(str(Y_MAP_DIRECTORY.joinpath(save_filename).resolve()), y_values)
            np.save(str(OBJECT_SPAWN_MAP_DIRECTORY.joinpath(save_filename).resolve()), object_spawns)

            # Save the surface data.
            SURFACE_MAP_DIRECTORY.joinpath(save_filename + ".json").write_text(dumps(surfaces, sort_keys=True))
            print(scene, layout)
            if not is_standalone:
                c.communicate({"$type": "pause_editor"})
    c.communicate({"$type": "terminate"})
    SCENE_BOUNDS_PATH.write_text(dumps(bounds, indent=2, sort_keys=True))
