import numpy as np
from enum import Enum
from typing import List, Tuple
from tdw.tdw_utils import TDWUtils
from tdw.controller import Controller
from tdw.output_data import Transforms
from sticky_mitten_avatar.tasks.task import Task
from sticky_mitten_avatar.avatar import Avatar
from sticky_mitten_avatar.util import get_object_indices, get_data


class _TurnState(Enum):
    """
    The current state of the turn.
    """

    ongoing = 1,
    success = 2,
    failure = 4


class TurnTo(Task):
    """
    Turn to face a target object.
    The avatar will re-adjust the turn if the object moves.
    """

    def __init__(self, avatar: Avatar, target: int, force: float = 40, threshold: float = 0.1):
        """
        :param avatar: The avatar.
        :param target: The ID of the target object.
        :param force: Turn by this much force per attempt.
        :param threshold: The angle between the object and the avatar's forward directional vector must be less than
        this for the turn to be a success.
        """

        self.target = target
        self.target_position = TDWUtils.VECTOR3_ZERO
        self.force = force
        self.threshold = threshold
        super().__init__(avatar=avatar)

        self.direction = 1

    def do(self, c: Controller) -> bool:
        resp = c.communicate([])
        # Turn.
        self._turn(c, resp)
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
            self._turn(c, resp)
            state = self._get_state()
            if state == _TurnState.success:
                return True
            elif state == _TurnState.failure:
                return False
            i += 1
        return False

    def end(self, c: Controller, success: bool) -> None:
        # Stop rotating.
        c.communicate({"$type": "set_avatar_drag",
                       "drag": 1000,
                       "angular_drag": 1000,
                       "avatar_id": self.avatar.avatar_id})

    def _turn(self, c: Controller, resp: List[bytes]) -> None:
        """
        Turn by a little bit.

        :param c: The controller.
        :param resp: The most recent response from the build.
        """

        self.target_position = self._get_target_position(resp=resp)
        angle = self._get_angle(self.target_position)
        # Decide which direction to turn.
        if angle > 180:
            self.direction = -1
        else:
            self.direction = 1

        c.communicate([{"$type": "set_avatar_drag",
                        "drag": 1000,
                        "angular_drag": 0.05,
                        "avatar_id": self.avatar.avatar_id},
                       {"$type": "turn_avatar_by",
                        "torque": self.force * self.direction,
                        "avatar_id": "a"}])

    def _get_target_position(self, resp: List[bytes]) -> Tuple[float, float, float]:
        """
        Get the target position.

        :param resp: The response from the build.
        """

        tr_index, ri_index = get_object_indices(resp=resp, o_id=self.target)
        return get_data(resp=resp, o_type=Transforms).get_position(tr_index)

    def _get_state(self) -> _TurnState:
        """
        Check if the avatar is aligned with the target.

        :return: Whether the turn is a success, failure, or ongoing.
        """

        angle = self._get_angle(self.target_position)

        if angle > 180:
            angle -= 360

        # Success because the avatar is facing the target.
        if np.abs(angle) < self.threshold:
            return _TurnState.success

        return _TurnState.ongoing
