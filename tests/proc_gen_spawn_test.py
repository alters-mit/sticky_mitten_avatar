import numpy as np
from tdw.output_data import Transforms
from sticky_mitten_avatar import StickyMittenAvatarController
from sticky_mitten_avatar.util import get_data


"""
Check that target objects and containers generally don't fall from their starting positions.
"""

if __name__ == "__main__":
    c = StickyMittenAvatarController()
    for scene in ["1a", "2a", "4a", "5a"]:
        for layout in [0, 1, 2]:
            print(scene, layout)
            c.init_scene(scene=scene, layout=layout)
            # Get the initial positions of each target object and container.
            positions = dict()
            for object_id in c.frame.object_transforms:
                if c.static_object_info[object_id].container or c.static_object_info[object_id].target_object:
                    positions[object_id] = c.frame.object_transforms[object_id].position

            # Advance the simulation.
            for i in range(100):
                c.communicate([])

            # Get the new position of the objects.
            resp = c.communicate({"$type": "send_transforms"})
            tr = get_data(resp=resp, d_type=Transforms)
            distances = list()
            too_far = False
            for i in range(tr.get_num()):
                object_id = tr.get_id(i)
                if object_id in positions:
                    distance = np.linalg.norm(positions[object_id] - np.array(tr.get_position(i)))
                    if distance > 0.1:
                        print(object_id, distance)
                        too_far = True
            if not too_far:
                print("Good!\n")
    c.end()
