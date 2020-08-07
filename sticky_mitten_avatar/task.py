from enum import Enum
from typing import List, Tuple, Dict
from abc import ABC, abstractmethod
from sticky_mitten_avatar.avatar import Avatar


class TaskState(Enum):
    """
    The current state of a task.
    """

    # Currently doing the task.
    doing = 1,
    # The task ended in success.
    success = 2,
    # The task ended in failure.
    failure = 4


class Task(ABC):
    """
    A task for the avatar to perform.
    """

    def __init__(self, avatar: Avatar):
        """
        :param avatar: The avatar doing the task.
        """

        self.avatar = avatar

    def on_frame(self, resp: List[bytes]) -> Tuple[List[dict], TaskState]:
        """
        Decide what to do on this frame given the simulation state.

        :param resp: The response from the build.

        :return: Commands to do something on this frame, and whether the task succeeded/failed/is ongoing.
        """

        if self._is_failure(resp):
            return [], TaskState.failure
        elif self._is_success(resp):
            return [], TaskState.success
        else:
            return self._on_frame(resp), TaskState.doing

    @abstractmethod
    def _is_failure(self, resp: List[bytes]) -> bool:
        """
        :param resp: The response from the build.

        :return: True if the avatar tried and failed to complete the task.
        """

        raise Exception()

    def _is_success(self, resp: List[bytes]) -> bool:
        """
        :param resp: The response from the build.

        :return: True if the avatar successfully completed the task on this frame.
        """

        raise Exception()

    def _on_frame(self, resp: List[bytes]) -> List[dict]:
        """
        Decide what to do on this frame.

        :param resp: The response from the build.

        :return: Commands to do something on this frame.
        """

        raise Exception()
