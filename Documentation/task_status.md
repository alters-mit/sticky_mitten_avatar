# `task_status.py`

## `TaskStatus(Enum)`

`from sticky_mitten_avatar.sticky_mitten_avatar.task_status import TaskStatus`

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

| Value | Description |
| --- | --- |
| `idle` | The avatar is not doing a task. |
| `ongoing` | The avatar is doing a task. |
| `success` | The avatar's task was successful. |
| `too_close_to_reach` | The avatar didn't try to reach for the target because it's too close. |
| `too_far_to_reach` | The avatar didn't try to reach for the target because it's too far away. |
| `behind_avatar` | The avatar didn't try to reach for the target because it's behind the avatar. |
| `no_longer_bending` | The avatar tried to reach the target, but failed; the arm is no longer bending. |
| `failed_to_pick_up` | The avatar bent its arm to reach for the object, but failed to pick it up. |
| `too_long` | The avatar stopped turning or moving because it tried for too many (>= 200) frames. |
| `overshot` | The avatar stopped moving because it overshot the target. |
| `collided_with_something_heavy` | The avatar stopped moving because collided with something heavy (mass > 90). |
| `collided_with_environment` | The avatar stopped moving because it collided with the environment, e.g. a wall. |
| `bad_raycast` | The avatar tried to cast array to the object but the ray was obstructed. |
| `failed_to_tap` | The avatar tried to tap the object but the mitten never collided with it. |
| `mitten_collision` | The avatar bent its arm but stopped part-way because the mitten collided with an object. |
| `not_in_container` | The avatar tried to drop an object in a container but the object isn't in the container. |
| `bad_joint` | This joint doesn't exist. |
| `not_a_container` | The avatar didn't try to put one object into another because the other object isn't a container. |

***

