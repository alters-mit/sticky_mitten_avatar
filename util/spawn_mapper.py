from pathlib import Path
import json
import numpy as np
from tdw.controller import Controller
from tdw.output_data import Environments
from tdw.tdw_utils import TDWUtils
from sticky_mitten_avatar.util import get_data, SCENE_BOUNDS_PATH, SPAWN_POSITIONS_PATH, OCCUPANCY_CELL_SIZE

"""
Calculate avatar spawn positions per scene per layout.
A spawn location is at the nearest free point to the center of the room.
Free points are determined with occupancy maps.
Rooms are determined with Environments output data.
"""


if __name__ == "__main__":
    p = Path("../sticky_mitten_avatar/occupancy_maps")
    sbd = json.loads(SCENE_BOUNDS_PATH.read_text())

    c = Controller()
    spawn_positions = dict()
    # Iterate through each floorplan scene.
    for scene in [1, 2, 4, 5]:
        print(scene)
        spawn_positions[scene] = dict()

        # Get the scene bounds (use this to get the actual (x, z) coordinates).
        scene_bounds = sbd[str(scene)]

        # Load the scene and request Environments data.
        resp = c.communicate([c.get_add_scene(scene_name=f"floorplan_{scene}a"),
                              {"$type": "send_environments"}])
        envs = get_data(resp=resp, d_type=Environments)

        # Get the center of each room.
        centers = []
        for i in range(envs.get_num()):
            centers.append(np.array(envs.get_center(i)))

        # Get the spawn positions per layout.
        for layout in [0, 1, 2]:
            spawn_positions[scene][layout] = list()
            for center in centers:
                # Load the occupancy map.
                occ = np.load(str(p.joinpath(f"{scene}_{layout}.npy").resolve()))

                # Get the free position on the map closest to the center of the room.
                min_distance = 1000
                min_position = None
                for ix, iy in np.ndindex(occ.shape):
                    if occ[ix, iy] == 1:
                        x = scene_bounds["x_min"] + (ix * OCCUPANCY_CELL_SIZE)
                        z = scene_bounds["z_min"] + (iy * OCCUPANCY_CELL_SIZE)
                        pos = np.array([x, 0, z])
                        d = np.linalg.norm(pos - center)
                        if d < min_distance:
                            min_distance = d
                            min_position = pos
                # Add the free position closest to the center as a spawn position.
                spawn_positions[scene][layout].append(TDWUtils.array_to_vector3(min_position))
    SPAWN_POSITIONS_PATH.write_text(json.dumps(spawn_positions, indent=2, sort_keys=True))
    c.communicate({"$type": "terminate"})
