import numpy as np
from typing import Tuple
from abc import ABC, abstractmethod
from tdw.controller import Controller
from sticky_mitten_avatar.avatar import Avatar


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

    def _get_angle(self, position: Tuple[float, float, float]) -> float:
        """
        :param position: The target position.

        :return: The angle in degrees between the avatar's forward directional vector and the position.
        """

        avatar_forward = self.avatar.avsm.get_forward()

        # Get the normalized directional vector to the target position.
        d = np.array(position) - self.avatar.avsm.get_position()
        d = d / np.linalg.norm(d)

        ang1 = np.arctan2(avatar_forward[2], avatar_forward[0])
        ang2 = np.arctan2(d[2], d[0])

        return np.rad2deg((ang1 - ang2) % (2 * np.pi))
