import numpy as np
from enum import Enum
from typing import List, Dict, Tuple
from tdw.controller import Controller
from tdw.output_data import Transforms
from sticky_mitten_avatar.tasks.task import Task
from sticky_mitten_avatar.avatar import Avatar
from sticky_mitten_avatar.util import get_data


class _TurnState(Enum):
    ongoing = 1,
    success = 2,
    failure = 4


class TurnTo(Task):
    """
    Turn to a target position.
    """

    def __init__(self, avatar: Avatar, target: Tuple[float, float, float], force: float = 40, threshold: float = 0.1):
        """
        :param avatar: The avatar.
        :param target: The target position.
        :param force: Turn by this much force per attempt.
        :param threshold: The angle between the object and the avatar's forward directional vector must be less than
        this for the turn to be a success.
        """

        self.target = target
        self.force = force
        self.threshold = threshold
        super().__init__(avatar=avatar)

        self.initial_angle = self._get_angle(target)
        # Decide which direction to turn.
        if self.initial_angle > 180:
            self.direction = -1
        else:
            self.direction = 1

    def do(self, c: Controller) -> bool:
        # Turn.
        self._turn(c)
        i = 0
        while i < 200:
            # Coast to a stop.
            coasting = True
            while coasting:
                coasting = np.linalg.norm(self.avatar.avsm.get_angular_velocity()) > 0.05
                state = self._get_state()
                if state == _TurnState.success:
                    return True
                elif state == _TurnState.failure:
                    return False
                c.communicate([])

            # Turn.
            self._turn(c)
            state = self._get_state()
            if state == _TurnState.success:
                return True
            elif state == _TurnState.failure:
                return False
            i += 1
        return False

    def end(self, c: Controller, success: bool) -> None:
        # Stop rotating.
        c.communicate([{"$type": "set_avatar_drag",
                        "drag": 1000,
                        "angular_drag": 0.05,
                        "avatar_id": self.avatar.avatar_id},
                       {"$type": "turn_avatar_by",
                        "torque": self.force * self.direction,
                        "avatar_id": "a"}])

    def _turn(self, c: Controller) -> None:
        """
        Turn by a little bit.

        :param c: The controller.
        """

        c.communicate([{"$type": "set_avatar_drag",
                        "drag": 1000,
                        "angular_drag": 0.05,
                        "avatar_id": self.avatar.avatar_id},
                       {"$type": "turn_avatar_by",
                        "torque": self.force * self.direction,
                        "avatar_id": "a"}])


    def _get_state(self) -> _TurnState:
        """
        Check if the avatar is aligned with the target.

        :return: Whether the turn is a success, failure, or ongoing.
        """

        angle = self._get_angle(self.target)

        # Failure because the avatar turned all the way around without aligning with the target.
        if angle - self.initial_angle >= 360:
            return _TurnState.failure

        if angle > 180:
            angle -= 360

        # Success because the avatar is facing the target.
        if np.abs(angle) < self.threshold:
            return _TurnState.success

        return _TurnState.ongoing
