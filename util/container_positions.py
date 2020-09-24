from json import dumps
from pathlib import Path
import numpy as np
from tdw.floorplan_controller import FloorplanController
from tdw.output_data import Environments, Raycast

"""
Get all flat surfaces in a floorplan+layout that a container can be based on and save these positions to a json file.
"""

if __name__ == "__main__":
    c = FloorplanController(launch_build=False)
    # This is the minimum size of a surface.
    r = 0.2
    scenes = dict()
    for scene in ["2"]:
        scenes[scene] = dict()
        for layout in [0, 1, 2]:
            print(scene, layout)
            # Load the scene and layout.
            commands = c.get_scene_init_commands(scene=scene + "a", layout=layout, audio=False)
            # Get the locations and sizes of each room.
            commands.append({"$type": "send_environments"})
            resp = c.communicate(commands)
            env = Environments(resp[0])
            positions = []
            # Iterate through each room.
            for i in range(env.get_num()):
                center = env.get_center(i)
                bounds = env.get_bounds(i)
                x = center[0] - (bounds[0] / 2)
                # Iterate through the area of the room as a grid where each cell is of size r.
                while x < center[0] + (bounds[0] / 2):
                    z = center[2] - (bounds[2] / 2)
                    while z < center[2] + (bounds[2] / 2):
                        # Spherecast at the "cell".
                        resp = c.communicate({"$type": "send_spherecast",
                                              "origin": {"x": x, "y": 2.3, "z": z},
                                              "destination": {"x": x, "y": 0, "z": z},
                                              "radius": r})
                        # Get the y values of each position in the spherecast.
                        ys = []
                        for j in range(len(resp) - 1):
                            raycast = Raycast(resp[j])
                            ys.append(raycast.get_point()[1])
                        y = max(ys)
                        # This is a valid position for a container if:
                        # 1. The spherecast hit something.
                        # 2. There is a low variance between y values (implying a flat surface).
                        # 3. The surface isn't too high up.
                        if len(ys) > 0 and np.var(np.array(ys)) < 0.1 and y <= 0.3:
                            positions.append({"x": x, "y": y, "z": z})
                        z += r * 2
                    x += r * 2
            scenes[scene][str(layout)] = positions
            print(scenes)
    c.communicate({"$type": "terminate"})
    Path("container_positions.json").write_text(dumps(scenes))
