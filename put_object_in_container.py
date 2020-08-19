from random import random
import numpy as np
from tdw.tdw_utils import TDWUtils
from tdw.librarian import ModelLibrarian
from sticky_mitten_avatar.avatars import Arm
from sticky_mitten_avatar.sma_controller import StickyMittenAvatarController


if __name__ == "__main__":
    c = StickyMittenAvatarController(launch_build=False)
    c.start()
    commands = [TDWUtils.create_empty_room(12, 12)]
    object_ids = []

    # The radius of the circle of objects.
    r = 1
    # The mass of each object.
    mass = 5
    spacing = 0.75
    balls_origin = (1, 2)

    # Get all points within the circle defined by the radius.
    p0 = np.array((0, 0))
    o_id = 0
    for x in np.arange(-r, r, spacing):
        for z in np.arange(-r, r, spacing):
            p1 = np.array((x, z))
            dist = np.linalg.norm(p0 - p1)
            if dist < r:
                o_id = c.get_unique_id()
                object_ids.append(o_id)
                commands.extend(c.get_add_object(model_name="sphere",
                                                 object_id=o_id,
                                                 position={"x": x + balls_origin[0], "y": 0, "z": z + balls_origin[1]},
                                                 mass=mass,
                                                 library="models_flex.json",
                                                 scale=0.1))
                # Set a random color.
                commands.append({"$type": "set_color",
                                 "color": {"r": random(),
                                           "g": random(),
                                           "b": random(),
                                           "a": 1.0},
                                 "id": o_id})
    bowl_id = c.get_unique_id()
    bowl_position = {"x": 1.2, "y": 0, "z": 0.25}
    commands.extend(c.get_add_object("serving_bowl",
                                     position=bowl_position,
                                     rotation={"x": 0, "y": 30, "z": 0},
                                     object_id=bowl_id,
                                     scale=1.3,
                                     library="models_core.json",
                                     mass=1000))
    c.communicate(commands)

    # Create the avatar.
    avatar_id = "a"
    c.create_avatar(avatar_id=avatar_id, debug=True)

    # Add a third-person camera.
    c.add_overhead_camera({"x": -0.08, "y": 1.25, "z": 1.41}, target_object=avatar_id, images="cam")

    # Put each object in the container.
    for o_id in object_ids:
        # Pick up the object.
        c.put_object_in_container(avatar_id=avatar_id, object_id=o_id, container_id=bowl_id)
