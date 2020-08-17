from typing import Dict, Union, List, Tuple, Optional
import numpy as np
from abc import ABC, abstractmethod
from ikpy.chain import Chain
from enum import Enum
from tdw.controller import Controller
from tdw.tdw_utils import TDWUtils
from tdw.output_data import OutputData, AvatarStickyMittenSegmentationColors, AvatarStickyMitten


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


class _Avatar(ABC):
    """
    A sticky mitten avatar. Contains high-level "Task" API and IK system.
    """

    def __init__(self, c: Controller, avatar_id: str = "a", position: Dict[str, float] = None):
        """
        Add a controller to the scene and cache the static data.
        The simulation will advance 1 frame.

        :param c: The controller.
        :param avatar_id: The ID of the avatar.
        :param position: The initial position of the avatar.
        """

        self.id = avatar_id
        # Set the arm chains.
        self._arms: Dict[Arm, Chain] = {Arm.left: self._get_left_arm(),
                                        Arm.right: self._get_right_arm()}
        # Any current IK goals.
        self._ik_goals: Dict[Arm, Optional[_IKGoal]] = {Arm.left: None,
                                                        Arm.right: None}

        if position is None:
            position = {"x": 0, "y": 0, "z": 0}
        # Create the avatar.
        commands = TDWUtils.create_avatar(avatar_type=self._get_avatar_type(),
                                          avatar_id=self.id,
                                          position=position)[:]
        # Request segmentation colors, body part names, and dynamic avatar data.
        # Turn off the follow camera.
        # Set the palms to sticky.
        commands.extend([{"$type": "send_avatar_segmentation_colors",
                          "frequency": "once",
                          "ids": [self.id]},
                         {"$type": "send_avatars",
                          "ids": [self.id],
                          "frequency": "always"},
                         {"$type": "toggle_image_sensor",
                          "sensor_name": "FollowCamera",
                          "avatar_id": self.id},
                         {"$type": "set_stickiness",
                          "sub_mitten": "palm",
                          "sticky": True,
                          "is_left": True,
                          "avatar_id": self.id},
                         {"$type": "set_stickiness",
                          "sub_mitten": "palm",
                          "sticky": True,
                          "is_left": False,
                          "avatar_id": self.id},
                         {"$type": "set_avatar_collision_detection_mode",
                          "mode": "continuous_dynamic",
                          "avatar_id": self.id},
                         {"$type": "adjust_joint_force_by",
                          "delta": 2,
                          "joint": "shoulder_right",
                          "axis": "pitch"},
                         {"$type": "adjust_joint_force_by",
                          "delta": 20,
                          "joint": "wrist_right",
                          "axis": "roll"},
                         {"$type": "adjust_joint_force_by",
                          "delta": 2,
                          "joint": "shoulder_left",
                          "axis": "pitch"},
                         {"$type": "adjust_joint_force_by",
                          "delta": 20,
                          "joint": "wrist_left",
                          "axis": "roll"}])

        # Send the commands. Get a response.
        resp = c.communicate(commands)
        avsc: Optional[AvatarStickyMittenSegmentationColors] = None
        for i in range(len(resp) - 1):
            r_id = OutputData.get_data_type_id(resp[i])
            if r_id == "avsc":
                q = AvatarStickyMittenSegmentationColors(resp[i])
                if q.get_id() == self.id:
                    avsc = q
                    break
        assert avsc is not None, f"No avatar segmentation colors found for {self.id}"

        # Cache static data of body parts.
        self.body_parts_static: Dict[str, BodyPartStatic] = dict()
        for i in range(avsc.get_num_body_parts()):
            bps = BodyPartStatic(o_id=avsc.get_body_part_id(i),
                                 color=avsc.get_body_part_segmentation_color(i))
            self.body_parts_static[avsc.get_body_part_name(i)] = bps

        # Get data for the current frame.
        # Start dynamic data.
        self.frame = self._get_frame(resp)

    def bend_arm_ik(self, arm: Arm, target: Union[np.array, list]) -> List[dict]:
        """
        Get an IK solution to a target position.

        :param arm: The arm (left or right).
        :param target: The target position for the mitten.

        :return: A list of commands to begin bending the arm.
        """

        # Get the IK solution.
        rotations = self._arms[arm].inverse_kinematics(target_position=target)
        commands = []
        a = arm.name
        for c, r in zip(self._arms[arm].links[1:], rotations[1:]):
            j = c.name.split("_")
            commands.append({"$type": "bend_arm_joint_to",
                             "angle": np.rad2deg(r),
                             "joint": f"{j[0]}_{a}",
                             "axis": j[1],
                             "avatar_id": self.id})
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
                for i in range(frame.get_num_rigidbody_parts()):
                    # Get the mitten.
                    if frame.get_body_part_id(i) == self.body_parts_static[f"mitten_{arm.name}"].o_id:
                        # If we're at the position, stop.
                        if np.linalg.norm(np.array(frame.get_body_part_position(i)) -
                                          self._ik_goals[arm].target) <= 0.1:
                            commands.extend(self._stop_arms())
                            temp_goals[arm] = None
                        else:
                            # Are we trying to pick up an object?
                            if self._ik_goals[arm].pick_up_id is not None:
                                # Did we pick up the object in the previous frame?
                                if self._ik_goals[arm].pick_up_id in frame.get_held_left() or self._ik_goals[arm].\
                                        pick_up_id in frame.get_held_right():
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
        # TODO check if the arm has stopped moving.
        self.frame = frame
        return commands

    @abstractmethod
    def _get_avatar_type(self) -> str:
        """
        :return: The avatar type (used for the `create_avatar` command).
        """

        raise Exception()

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
        for arm in self._arms:
            a = arm.name
            for link in self._arms[arm].links[1:]:
                j = link.name.split("_")

                commands.append({"$type": "stop_arm_joint",
                                 "joint": f"{j[0]}_{a}",
                                 "axis": j[1],
                                 "avatar_id": self.id})
        return commands
