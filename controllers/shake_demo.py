from sticky_mitten_avatar import BoxRoomContainers
from sticky_mitten_avatar.avatars import Arm


"""
A demo of an avatar shaking boxes. Each box has a different number of objects. 
Each group of objects has a different audio material. The avatar will shake each box and then "decide" which box to put
on the sofa.
"""


if __name__ == "__main__":
    c = BoxRoomContainers(audio_playback_mode="unity", launch_build=True)
    # Initialize the scene. Add the objects, avatar, set global values, etc.
    c.init_scene()

    # Pick up each container, shake it, and put it down.
    for container in [c.container_0, c.container_1]:
        c.go_to(avatar_id=c.avatar_id, target=container, move_stopping_threshold=0.7)
        arm = c.pick_up(avatar_id=c.avatar_id, object_id=container)

        c.bend_arm(avatar_id=c.avatar_id, arm=arm,
                   target={"x": 0.1 * 1 if arm == Arm.right else -1, "y": 0.4, "z": 0.485})
        c.shake(avatar_id=c.avatar_id, joint_name=f"elbow_{arm.name}")
        c.put_down(avatar_id=c.avatar_id, do_motion=False)
    # Pick up the first container again.
    c.go_to(avatar_id=c.avatar_id, target=c.container_0, move_stopping_threshold=0.7)
    c.turn_to(avatar_id=c.avatar_id, target=c.container_0)
    c.pick_up(avatar_id=c.avatar_id, object_id=c.container_0)

    # Put the container on the sofa.
    # The "target" values are hardcoded for now; in the future, there will be better avatar navigation.
    c.go_to(avatar_id=c.avatar_id,
            target={"x": 1.721, "y": 0, "z": -1.847},
            turn_stopping_threshold=2,
            move_stopping_threshold=0.2)
    c.turn_to(avatar_id=c.avatar_id, target={"x": 2.024, "y": 0.46, "z": -2.399})
    c.put_down(avatar_id=c.avatar_id)
    c.end()
