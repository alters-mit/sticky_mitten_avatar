from sticky_mitten_avatar.box_room_containers import BoxRoomContainers
from sticky_mitten_avatar.avatars import Arm


"""
A demo of an avatar shaking boxes. Each box has a different number of objects. 
Each group of objects has a different audio material. The avatar will shake each box and then "decide" which box to put
on the sofa.
"""


if __name__ == "__main__":
    c = BoxRoomContainers(demo=True)
    # Initialize the scene. Add the objects, avatar, set global values, etc.
    c.init_scene()

    # Pick up each container, shake it, and put it down.
    for container, arm in zip([c.container_0, c.container_1], [Arm.left, Arm.right]):
        c.go_to(target=container, move_stopping_threshold=0.7, turn_force=700)
        c.grasp_object(object_id=container, arm=arm)
        c.shake(joint_name=f"elbow_{arm.name}")
        c.drop(do_motion=False)
    # Pick up the first container again.
    c.go_to(target=c.container_0, move_stopping_threshold=0.7)
    c.turn_to(target=c.container_0)
    c.grasp_object(object_id=c.container_0, arm=Arm.left)

    # Put the container on the sofa.
    # The "target" values are hardcoded for now; in the future, there will be better avatar navigation.
    c.go_to(target={"x": 1.721, "y": 0, "z": -1.847}, turn_stopping_threshold=2, move_stopping_threshold=0.2)
    c.turn_to(target={"x": 2.024, "y": 0.46, "z": -2.399})
    c.reach_for_target(arm=Arm.left, target={"x": 0, "y": 0.4, "z": 1}, do_motion=False)
    for i in range(20):
        c.communicate([])
    c.drop()
    c.end()
