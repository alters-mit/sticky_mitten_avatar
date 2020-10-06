from enum import Enum


class TaskStatus(Enum):
    """
    The current status of an avatar: whether it is doing a task, succeeded at a task, or failed a task (and if so, why).

    Usage:

    ```python
    from sticky_mitten_avatar import StickyMittenAvatarController, Arm

    c = StickyMittenAvatarController()
    c.init_scene()
    status = c.reach_for_target(target={"x": 0, "y": 0, "z": 0}, arm=Arm.left)
    print(status) # TaskStatus.too_close_to_reach
    print(status.name) # "too_close_to_reach"
    ```

    In the table below, if the avatar "didn't try" to do a task, it indicates that the task immediately failed.
    Otherwise, the avatar may have tried moving, turning, bending an arm, etc. before the task failed.
    """

    idle = 1  # The avatar is not doing a task.
    ongoing = 2  # The avatar is doing a task.
    success = 4  # The avatar's task was successful.
    too_close_to_reach = 8  # The avatar didn't try to reach for the target because it's too close.
    too_far_to_reach = 16  # The avatar didn't try to reach for the target because it's too far away.
    behind_avatar = 32  # The avatar didn't try to reach for the target because it's behind the avatar.
    no_longer_bending = 64  # The avatar tried to reach the target, but failed; the arm is no longer bending.
    failed_to_pick_up = 128  # The avatar bent its arm to reach for the object, but failed to pick it up.
    too_long = 256  # The avatar stopped turning or moving because it tried for too many (>= 200) frames.
    overshot = 512  # The avatar stopped moving because it overshot the target.
    collided_with_something_heavy = 1024  # The avatar stopped moving because collided with something heavy (mass > 90).
    collided_with_environment = 2048  # The avatar stopped moving because it collided with the environment, e.g. a wall.
    bad_raycast = 4096  # The avatar tried to cast array to the object but the ray was obstructed.
    failed_to_tap = 8196  # The avatar tried to tap the object but the mitten never collided with it.
    mitten_collision = 16392  # The avatar bent its arm but stopped part-way because the mitten collided with an object.
    not_in_container = 32784  # The avatar tried to drop an object in a container but the object isn't in the container.
    bad_joint = 65568  # This joint doesn't exist.
