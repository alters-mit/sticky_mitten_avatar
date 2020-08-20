from tdw.tdw_utils import TDWUtils
from sticky_mitten_avatar.avatars import Arm
from sticky_mitten_avatar.sma_controller import StickyMittenAvatarController


if __name__ == "__main__":
    # Create and start the controller.
    c = StickyMittenAvatarController(launch_build=False)
    c.start()

    o_id = c.get_unique_id()
    commands = [TDWUtils.create_empty_room(12, 12)]
    # Add the jug.
    commands.extend(c.get_add_object("jug05",
                                     position={"x": -0.2, "y": 0, "z": 0.385},
                                     object_id=o_id,
                                     scale={"x": 0.8, "y": 0.8, "z": 0.8}))
    bowl_id = c.get_unique_id()
    bowl_position = {"x": 1.2, "y": 0, "z": 0.25}
    commands.extend(c.get_add_object("serving_bowl",
                                     position=bowl_position,
                                     rotation={"x": 0, "y": 30, "z": 0},
                                     object_id=bowl_id,
                                     scale={"x": 1.3, "y": 1, "z": 1.3},
                                     mass=1000))
    c.communicate(commands)

    avatar_id = "a"
    c.create_avatar(avatar_id=avatar_id)

    # Add a third-person camera.
    c.add_overhead_camera({"x": -0.08, "y": 1.25, "z": 1.41}, target_object=avatar_id, images="cam")

    # Pick up the object.
    c.pick_up(avatar_id=avatar_id, object_id=o_id)
    # Lift the object up a bit.
    c.bend_arm(avatar_id=avatar_id, target={"x": -0.1, "y": 0.4, "z": 0.42}, arm=Arm.left)
    # Go to the bowl.
    c.go_to(avatar_id=avatar_id, target=bowl_id)
    # Lift the object up a bit.
    c.bend_arm(avatar_id=avatar_id, target={"x": 1.178, "y": 0.4, "z": 0.34}, arm=Arm.left)
    # Drop the object in the container.
    c.put_down(avatar_id=avatar_id)
    for i in range(50):
        c.communicate([])
