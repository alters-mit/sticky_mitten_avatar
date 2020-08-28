from sticky_mitten_avatar import BoxRoomContainers
from sticky_mitten_avatar.avatars import Arm


if __name__ == "__main__":
    c = BoxRoomContainers(launch_build=False)
    # Initialize the scene. Add the objects, avatar, set global values, etc.
    c.init_scene()

    # Pick up each container, shake it, and put it down.
    for container, arm, x_dir in zip([c.container_0, c.container_1], [Arm.right, Arm.left], [1, -1]):
        c.go_to(avatar_id=c.avatar_id, target=container, move_stopping_threshold=0.7)
        c.pick_up(avatar_id=c.avatar_id, object_id=container)
        c.bend_arm(avatar_id=c.avatar_id, target={"x": 0.2 * x_dir, "y": 0.4, "z": 0.385}, arm=arm)
        c.shake(avatar_id=c.avatar_id, joint_name=f"elbow_{arm.name}")
        c.put_down(avatar_id=c.avatar_id, do_motion=True)
    # Pick up the first container again.
    c.go_to(avatar_id=c.avatar_id, target=c.container_0, move_stopping_threshold=0.3)
    c.pick_up(avatar_id=c.avatar_id, object_id=c.container_0)

    # Put the container on the sofa.
    # The "target" values are hardcoded for now; in the future, there will be better avatar navigation.
    c.bend_arm(avatar_id=c.avatar_id, target={"x": 0.026, "y": 0.2, "z": 0.66}, arm=Arm.right)
    c.go_to(avatar_id=c.avatar_id,
            target={"x": 1.721, "y": 0, "z": -1.847},
            turn_stopping_threshold=2,
            move_stopping_threshold=0.1)
    c.turn_to(avatar_id=c.avatar_id, target={"x": 2.024, "y": 0.46, "z": -2.399})
    c.put_down(avatar_id=c.avatar_id)
    c.end()
