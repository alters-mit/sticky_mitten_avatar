from abc import ABC, abstractmethod
import numpy as np
from typing import Tuple, List
from tdw.controller import Controller
from tdw.output_data import Bounds
from sticky_mitten_avatar import Avatar
from sticky_mitten_avatar.tasks import Task, TurnTo, TaskState
from sticky_mitten_avatar.util import get_data, get_closest_point_in_bounds


class _GoTo(Task, ABC):
    """
    Go to a target position.
    First, turn to face the position. Then, go to it.
    """

    def __init__(self, avatar: Avatar, turn_force: float = 40,
                 turn_threshold: float = 0.1, move_force: float = 45, move_threshold: float = 1):
        """
        :param avatar: The avatar.
        :param turn_force: Turn by this much force per attempt.
        :param move_force: Move by this much force per attempt.
        :param turn_threshold: The angle between the object and the avatar's forward directional vector must be less
        than this for the turn to be a success.
        :param move_threshold: Stop moving when we are this close to the object.
        """

        self.move_force = move_force
        self.move_threshold = move_threshold
        self.destination = self._get_destination()

        self.turn_task = TurnTo(avatar=avatar, target=self.destination, force=turn_force, threshold=turn_threshold)

        super().__init__(avatar=avatar)
        self.initial_distance = np.linalg.norm(np.array(self.avatar.avsm.get_position()) - self.destination)
        self.initial_position = np.array(self.avatar.avsm.get_position())

    def do(self, c: Controller) -> bool:
        # Turn to face the object.
        turned = self.turn_task.do(c)
        if not turned:
            return False
        self.turn_task.end(c, turned)

        i = 0
        while i < 200:
            # Start gliding.
            t = self._move_step([{"$type": "set_avatar_drag",
                                  "drag": 0.1,
                                  "angular_drag": 100,
                                  "avatar_id": self.avatar.avatar_id},
                                 {"$type": "move_avatar_forward_by",
                                  "magnitude": self.move_force,
                                  "avatar_id": self.avatar.avatar_id}], c)
            if t == TaskState.success:
                return True
            elif t == TaskState.failure:
                return False
            # Glide.
            while np.linalg.norm(self.avatar.avsm.get_velocity()) > 0.1:
                t = self._move_step([], c)
                if t == TaskState.success:
                    return True
                elif t == TaskState.failure:
                    return False
            i += 1
        return False

    def end(self, c: Controller, success: bool) -> None:
        c.communicate({"$type": "set_avatar_drag",
                       "drag": 1000,
                       "angular_drag": 100,
                       "avatar_id": self.avatar.avatar_id})
        while np.linalg.norm(self.avatar.avsm.get_velocity()) > 0.1:
            c.communicate([])

    def _move_step(self, commands: List[dict], c: Controller) -> TaskState:
        """
        Step through the movement. Move forward, coast, try again.

        :param commands: A list of commands to begin the movement.
        :param c: The controller.

        :return: The overall state of the task after this move.
        """

        c.communicate(commands)
        p = np.array(self.avatar.avsm.get_position())
        d_from_initial = np.linalg.norm(self.initial_position - p)
        # Overshot. End.
        if d_from_initial > self.initial_distance:
            return TaskState.failure
        # We're here! End.
        d = np.linalg.norm(p - self.destination)
        if d <= self.move_threshold:
            return TaskState.success
        # Keep truckin' along.
        return TaskState.ongoing

    @abstractmethod
    def _get_destination(self) -> np.array:
        """
        :return: The position the avatar will go to.
        """

        raise Exception()


class GoToPosition(_GoTo):
    """
    The avatar will try go to a destination position.
    First, the avatar will turn with a `TurnTo` task to face the position.
    Then, the avatar will try to move to the destination.
    """

    def __init__(self, avatar: Avatar, destination: Tuple[float, float, float], turn_force: float = 40,
                 turn_threshold: float = 0.1, move_force: float = 45, move_threshold: float = 1):
        """
        :param avatar: The avatar.
        :param destination: The destination position of the avatar.
        :param turn_force: Turn by this much force per attempt.
        :param move_force: Move by this much force per attempt.
        :param turn_threshold: The angle between the object and the avatar's forward directional vector must be less
        than this for the turn to be a success.
        :param move_threshold: Stop moving when we are this close to the object.
        """

        self.destination = np.array(destination)

        super().__init__(avatar=avatar, turn_force=turn_force, turn_threshold=turn_threshold, move_force=move_force,
                         move_threshold=move_threshold)

    def _get_destination(self) -> np.array:
        return self.destination


class GoToObject(_GoTo):
    """
    The avatar will try go to an object in the scene.
    The destination position is the point on the object's `Bounds` closest to the avatar.
    First, the avatar will turn with a `TurnTo` task to face the position.
    Then, the avatar will try to move to the destination.
    """

    def __init__(self, avatar: Avatar, object_id: int, c: Controller, turn_force: float = 40,
                 turn_threshold: float = 0.1, move_force: float = 45, move_threshold: float = 1):
        """
        :param avatar: The avatar.
        :param object_id: The ID of the target object.
        :param turn_force: Turn by this much force per attempt.
        :param move_force: Move by this much force per attempt.
        :param turn_threshold: The angle between the object and the avatar's forward directional vector must be less
        than this for the turn to be a success.
        :param move_threshold: Stop moving when we are this close to the object.
        :param c: The controller. Required in order to get the bounds data of the object.
        """

        # Get bounds data for the object.
        resp = c.communicate({"$type": "send_bounds",
                              "frequency": "once",
                              "ids": [object_id]})
        bounds = get_data(resp=resp, d_type=Bounds)

        # Convert the bounds data of the object to a dictionary. We know that there is only 1 object in the bounds.
        self.destination = get_closest_point_in_bounds(origin=np.array(self.avatar.avsm.get_position()),
                                                       bounds=bounds, index=0)

        super().__init__(avatar=avatar, turn_force=turn_force, turn_threshold=turn_threshold, move_force=move_force,
                         move_threshold=move_threshold)

    def _get_destination(self) -> np.array:
        return self.destination
