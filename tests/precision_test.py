from sticky_mitten_avatar import StickyMittenAvatarController, Arm
from sticky_mitten_avatar.task_status import TaskStatus


if __name__ == "__main__":
    c = StickyMittenAvatarController(launch_build=False)
    c.init_scene()

    for precision in [0.05, 0.1, 0.15, 0.2, 1]:
        status = c.reach_for_target(target={"x": -0.2, "y": 0.4, "z": 0.385}, arm=Arm.left, precision=precision)
        assert status == TaskStatus.success, status
        status = c.reset_arm(arm=Arm.left)
        assert status == TaskStatus.success, status
    c.end()
