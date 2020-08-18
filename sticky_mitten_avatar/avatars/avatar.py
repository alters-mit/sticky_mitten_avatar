from typing import Dict, Union, List, Tuple, Optional
import numpy as np
from abc import ABC, abstractmethod
from ikpy.chain import Chain
from enum import Enum
from tdw.output_data import OutputData, AvatarStickyMittenSegmentationColors, AvatarStickyMitten, Bounds


class Arm(Enum):
    """
    The side that an arm is on.
    """

    left = 0,
    right = 1


class BodyPartStatic:
    """
    Static data for a body part in an avatar.
    """

    def __init__(self, o_id: int, color: Tuple[float, float, float]):
        """
        :param o_id: The object ID of the part.
        :param color: The segmentation color of the part.
        """

        self.o_id = o_id
        self.color = color


class Joint:
    """
    A joint, a side, and an axis.
    """

    def __init__(self, part: str, arm: str, axis: str):
        """
        :param part: The name of the body part.
        :param axis: The axis of rotation.
        :param arm: The arm that the joint is attached to.
        """

        self.joint = f"{part}_{arm}"
        self.axis = axis


class _IKGoal:
    """
    The goal of an IK action.
    """

    def __init__(self, target: Union[np.array, list], pick_up_id: int = None):
        """
        :param pick_up_id: If not None, the ID of the object to pick up.
        :param target: The target position of the mitten.
        """

        self.pick_up_id = pick_up_id
        if isinstance(target, list):
            self.target = np.array(target)
        else:
            self.target = target


class Avatar(ABC):
    """
    A sticky mitten avatar. Contains high-level "Task" API and IK system.
    """

    JOINTS = [Joint(arm="left", axis="pitch", part="shoulder"),
              Joint(arm="left", axis="yaw", part="shoulder"),
              Joint(arm="left", axis="roll", part="shoulder"),
              Joint(arm="left", axis="pitch", part="elbow"),
              Joint(arm="left", axis="roll", part="wrist"),
              Joint(arm="left", axis="pitch", part="wrist"),
              Joint(arm="right", axis="pitch", part="shoulder"),
              Joint(arm="right", axis="yaw", part="shoulder"),
              Joint(arm="right", axis="roll", part="shoulder"),
              Joint(arm="right", axis="pitch", part="elbow"),
              Joint(arm="right", axis="roll", part="wrist"),
              Joint(arm="right", axis="pitch", part="wrist")]

    _ARM_OFFSETS = {Arm.left: np.array([-0.235, 0.565, 0.075]),
                    Arm.right: np.array([0.235, 0.565, 0.075])}

    def __init__(self, resp: List[bytes], avatar_id: str = "a", debug: bool = False):
        """
        Add a controller to the scene and cache the static data.
        The simulation will advance 1 frame.

        :param resp: The response from the build after creating the avatar.
        :param avatar_id: The ID of the avatar.
        :param debug: If True, print debug statements.
        """

        self.id = avatar_id
        self.debug = debug
        self._mitten_offset = self._get_mitten_offset()
        # Set the arm chains.
        self._arms: Dict[Arm, Chain] = {Arm.left: self._get_left_arm(),
                                        Arm.right: self._get_right_arm()}
        # Any current IK goals.
        self._ik_goals: Dict[Arm, Optional[_IKGoal]] = {Arm.left: None,
                                                        Arm.right: None}
        smsc: Optional[AvatarStickyMittenSegmentationColors] = None
        for i in range(len(resp) - 1):
            r_id = OutputData.get_data_type_id(resp[i])
            if r_id == "smsc":
                q = AvatarStickyMittenSegmentationColors(resp[i])
                if q.get_id() == avatar_id:
                    smsc = q
                    break
        assert smsc is not None, f"No avatar segmentation colors found for {avatar_id}"
        # Cache static data of body parts.
        self.body_parts_static: Dict[str, BodyPartStatic] = dict()
        for i in range(smsc.get_num_body_parts()):
            bps = BodyPartStatic(o_id=smsc.get_body_part_id(i),
                                 color=smsc.get_body_part_segmentation_color(i))
            self.body_parts_static[smsc.get_body_part_name(i)] = bps

        # Get data for the current frame.
        # Start dynamic data.
        self.frame = self._get_frame(resp)

    def bend_arm(self, arm: Arm, target: Union[np.array, list], target_orientation: np.array = None) -> List[dict]:
        """
        Get an IK solution to move a mitten to a target position.

        :param arm: The arm (left or right).
        :param target: The target position for the mitten.
        :param target_orientation: Target IK orientation. Usually you should leave this as None (the default).

        :return: A list of commands to begin bending the arm.
        """

        ik_target = np.array(target) - (self.frame.get_position() + self._ARM_OFFSETS[arm])
        if self.debug:
            print(f"IK target: {ik_target}")
        self._ik_goals[arm] = _IKGoal(target=target)

        # Get the IK solution.
        rotations = self._arms[arm].inverse_kinematics(target_position=ik_target, target_orientation=target_orientation)
        commands = []
        a = arm.name
        for c, r in zip(self._arms[arm].links, rotations):
            j = c.name.split("_")
            commands.append({"$type": "bend_arm_joint_to",
                             "angle": np.rad2deg(r),
                             "joint": f"{j[0]}_{a}",
                             "axis": j[1],
                             "avatar_id": self.id})
        return commands

    def pick_up(self, arm: Arm, object_id: int, bounds: Bounds) -> List[dict]:
        """
        Begin to try to pick up an object,
        Get an IK solution to a target position.

        :param arm: The arm (left or right).
        :param object_id: The ID of the target object.
        :param bounds: Bounds output data.

        :return: A list of commands to begin bending the arm.
        """

        center: Optional[np.array] = None
        nearest: Optional[np.array] = None
        nearest_distance = np.inf

        # Get the nearest point on the bounds.
        for i in range(bounds.get_num()):
            if bounds.get_id(i) == object_id:
                center = np.array(bounds.get_center(i))
                for p in [bounds.get_left(i), bounds.get_right(i), bounds.get_top(i), bounds.get_bottom(i),
                          bounds.get_front(i), bounds.get_back(i)]:
                    p = np.array(p)
                    d = np.linalg.norm(center - p)
                    if d < nearest_distance:
                        nearest = p
                        nearest_distance = d
        assert center is not None, f"Couldn't find center of object {object_id}"
        assert nearest is not None, f"Couldn't get nearest point of object {object_id}"

        nearest[1] = center[1]

        target_orientation = (center - nearest) / np.linalg.norm(center - nearest)

        commands = self.bend_arm(arm=arm, target=nearest, target_orientation=target_orientation)
        self._ik_goals[arm].pick_up_id = object_id
        return commands

    def on_frame(self, resp: List[bytes]) -> List[dict]:
        """
        Update the avatar based on its current arm-bending goals and its state.
        If the avatar has achieved a goal (for example, picking up an object), it will stop moving that arm.

        :param resp: The response from the build.

        :return: A list of commands to pick up, stop moving, etc.
        """

        # Update dynamic data.
        frame = self._get_frame(resp=resp)

        # Check if IK goals are done.
        temp_goals: Dict[Arm, Optional[_IKGoal]] = dict()
        # Get commands for the next frame.
        commands: List[dict] = []
        for arm in self._ik_goals:
            # No IK goal on this arm.
            if self._ik_goals[arm] is None:
                temp_goals[arm] = None
            else:
                # Is the arm at the target?
                mitten = f"mitten_{arm.name}"
                for i in range(frame.get_num_rigidbody_parts()):
                    # Get the mitten.
                    if frame.get_body_part_id(i) == self.body_parts_static[mitten].o_id:
                        mitten_position = np.array(frame.get_body_part_position(i)) - self._mitten_offset
                        # If we're at the position, stop.
                        d = np.linalg.norm(mitten_position - self._ik_goals[arm].target)
                        if d <= 0.08:
                            if self.debug:
                                print(f"{mitten} is at target position {self._ik_goals[arm].target}. Stopping.")
                            commands.extend(self._stop_arms())
                            temp_goals[arm] = None
                        else:
                            # Are we trying to pick up an object?
                            if self._ik_goals[arm].pick_up_id is not None:
                                # Did we pick up the object in the previous frame?
                                if self._ik_goals[arm].pick_up_id in frame.get_held_left() or self._ik_goals[arm].\
                                        pick_up_id in frame.get_held_right():
                                    if self.debug:
                                        print(f"{mitten} picked up {self._ik_goals[arm].pick_up_id}. Stopping.")
                                    commands.extend(self._stop_arms())
                                    temp_goals[arm] = None
                                # Keep bending the arm and trying to pick up the object.
                                else:
                                    commands.append({"$type": "pick_up_proximity",
                                                     "distance": 0.1,
                                                     "radius": 0.1,
                                                     "grip": 1000,
                                                     "is_left": arm == Arm.left,
                                                     "avatar_id": self.id,
                                                     "object_ids": [self._ik_goals[arm].pick_up_id]})
                                    temp_goals[arm] = self._ik_goals[arm]
                            # Keep bending the arm.
                            else:
                                temp_goals[arm] = self._ik_goals[arm]
                                self._ik_goals[arm].previous_distance = d
        self._ik_goals = temp_goals

        # Check if the arms are still moving.
        temp_goals: Dict[Arm, Optional[_IKGoal]] = dict()
        for arm in self._ik_goals:
            # No IK goal on this arm.
            if self._ik_goals[arm] is None:
                temp_goals[arm] = None
            else:
                # Get the past and present angles.
                if arm == Arm.left:
                    angles_0 = self.frame.get_angles_left()
                    angles_1 = frame.get_angles_left()
                else:
                    angles_0 = self.frame.get_angles_right()
                    angles_1 = frame.get_angles_right()
                # Is any joint still moving?
                moving = False
                for a0, a1 in zip(angles_0, angles_1):
                    if np.abs(a0 - a1) > 0.01:
                        moving = True
                        break
                # Keep moving.
                if moving:
                    temp_goals[arm] = self._ik_goals[arm]
                else:
                    if self.debug:
                        print(f"{arm.name} is no longer bending. Cancelling.")
                    temp_goals[arm] = None
        self._ik_goals = temp_goals
        self.frame = frame
        return commands

    def is_ik_done(self) -> bool:
        """
        :return: True if the IK goals are complete, False if the arms are still moving/trying to pick up/etc.
        """

        return self._ik_goals[Arm.left] is None and self._ik_goals[Arm.right] is None

    def is_holding(self, object_id: int) -> bool:
        """
        :param object_id: The ID of the object.

        :return: True if the avatar is holding the object in either mitten.
        """

        return object_id in self.frame.get_held_right() or object_id in self.frame.get_held_left()

    def put_down(self, reset_arms: bool = True) -> List[dict]:
        """
        Put down the object.

        :pa
        :param reset_arms: If True, reset arm positions to "neutral".

        :return: A list of commands to put down the object.
        """

        commands = [{"$type": "put_down",
                     "is_left": True,
                     "avatar_id": self.id},
                    {"$type": "put_down",
                     "is_left": False,
                     "avatar_id": self.id}]
        if reset_arms:
            for j in self.JOINTS:
                commands.append({"$type": "bend_arm_joint_to",
                                 "joint": j.joint,
                                 "axis": j.axis,
                                 "angle": 0,
                                 "avatar_id": self.id})
        return commands

    @abstractmethod
    def _get_left_arm(self) -> Chain:
        """
        :return: The IK chain of the left arm.
        """

        raise Exception()

    @abstractmethod
    def _get_right_arm(self) -> Chain:
        """
        :return: The IK chain of the right arm.
        """

        raise Exception()

    def _get_mitten_offset(self) -> np.array:
        """
        :return: The offset vector from the mitten position (at the wrist) to the centerpoint.
        """

        raise Exception()

    def _get_frame(self, resp: List[bytes]) -> AvatarStickyMitten:
        for i in range(len(resp) - 1):
            r_id = OutputData.get_data_type_id(resp[i])
            if r_id == "avsm":
                avsm = AvatarStickyMitten(resp[i])
                if avsm.get_avatar_id() == self.id:
                    return avsm
        raise Exception(f"No avatar data found for {self.id}")

    def _stop_arms(self) -> List[dict]:
        """
        :return: Commands to stop all arm movement.
        """

        commands = []
        for j in self.JOINTS:
            commands.append({"$type": "stop_arm_joint",
                             "joint": j.joint,
                             "axis": j.axis,
                             "avatar_id": self.id})
        return commands
