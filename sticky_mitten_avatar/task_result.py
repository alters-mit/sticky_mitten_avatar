from enum import Enum


class TaskResult(Enum):
    """
    The result of an API call that tells the avatar to do a task (e.g. `go_to()`).

    | Value | Meaning |
    | --- | --- |
    | `ok` | Task was successful. |
    | `too_close_to_reach` | The avatar can't reach for the target position or object because it is too close. |
    | `too_far_to_reach` | The avatar can't reach for the target position or object because it is too far away. |
    | `behind_avatar` | The avatar can't reach for the target position or object because it is behind the avatar. |
    |
    """

    ok = 1
    too_close_to_reach = 2
    too_far_to_reach = 4
    behind_avatar = 8
