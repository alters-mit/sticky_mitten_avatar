from enum import Enum
import numpy as np
from typing import Tuple
from abc import ABC, abstractmethod
from tdw.controller import Controller
from sticky_mitten_avatar.avatar import Avatar


class TaskState(Enum):
    """
    Describe the current state of the task.
    """
    ongoing = 1,
    success = 2,
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

    @abstractmethod
    def do(self, c: Controller) -> bool:
        """
        Do the task. Step through frames until the task either succeeds for fails.

        :param c: The controller.

        :return: True if the task succeeded, False if it failed.
        """

        raise Exception()

    @abstractmethod
    def end(self, c: Controller, success: bool) -> None:
        """
        Do something at the end of the task.

        :param c: The controller.
        :param success: True if the task was successful.
        """

        raise Exception()
