from pathlib import Path
import json
import numpy as np
from tdw.controller import Controller
from sticky_mitten_avatar.environments import Environments


if __name__ == "__main__":
    p = Path("../sticky_mitten_avatar/occupancy_maps")
    c = Controller()
    spawn_positions = dict()
    for f in p.glob("*.npy"):
        # Update the dictionary.
        scene = f.stem[0]
        layout = f.stem[-1]
        if scene not in spawn_positions:
            spawn_positions[scene] = dict()
        spawn_positions[scene][layout] = list()

        # Load the occupancy map.
        occ = np.load(str(f.resolve()))
        # Get the (x, z) coordinates.
        q = [(o[0], o[1]) for o in occ]

        # Load the scene and get environment data.
        resp = c.communicate([c.get_add_scene(scene_name=f"floorplan_{scene}a"),
                              {"$type": "send_environments"}])
        envs = Environments(resp=resp)
        for env in envs.envs:
            # Get all empty positions in this environment.
            empty_positions = [p for p in q if env.is_inside(x=p[0], z=p[1])]
            if len(empty_positions) == 0:
                print("Warning! No empty positions!")
                continue
            # Get the average of all empty positions.
            avg = np.mean(empty_positions, axis=0)
            # Get the empty position closest to the average of the empty positions. This is the center.
            min_norm = 1000
            spawn = None
            for ep in empty_positions:
                ep = np.array(ep)
                n = np.linalg.norm(ep - avg)
                if n < min_norm:
                    min_norm = n
                    spawn = ep
            # Add this as a spawn position.
            if spawn is not None:
                spawn_positions[scene][layout].append({"x": float(spawn[0]), "y": 0, "z": float(spawn[1])})

    Path("../sticky_mitten_avatar/occupancy_maps/spawn_positions.json").write_text(json.dumps(spawn_positions,
                                                                                              indent=2))
