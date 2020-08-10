from enum import Enum
import numpy as np
from typing import Dict, Tuple, List, Union
from tdw.tdw_utils import TDWUtils
from tdw.controller import Controller
from tdw.output_data import AvatarStickyMittenSegmentationColors, AvatarStickyMitten
from sticky_mitten_avatar.util import get_data
from sticky_mitten_avatar.entity import Entity


class _Axis(Enum):
    """
    An axis of rotation.
    """

    pitch = 1
    yaw = 2
    roll = 4


class _JointType(Enum):
    """
    A type of joint.
    """

    shoulder = 1
    elbow = 2
    wrist = 4


class Joint(Enum):
    """
    A joint (shoulder, elbow, wrist), side (left or right), and axis of rotation (pitch, yaw, roll).
    See: `Avatar.bend_arm_joints`
    """

    shoulder_left_pitch = 1
    shoulder_left_yaw = 2
    shoulder_left_roll = 4
    elbow_left_pitch = 8
    wrist_left_pitch = 16
    wrist_left_roll = 32
    shoulder_right_pitch = 64
    shoulder_right_yaw = 128
    shoulder_right_roll = 256
    elbow_right_pitch = 512
    wrist_right_pitch = 1024
    wrist_right_roll = 2048


class _Joint:
    """
    A type of joint an an axis.
    """

    def __init__(self, joint_type: _JointType, axis: _Axis, left: bool):
        """
        :param joint_type: The type of the joint.
        :param axis: The axis of rotation.
        :param left: If True, this is the left arm.
        """

        self.joint_type = joint_type
        self.axis = axis
        self.left = left

    def get_bend_by(self, angle: float, avatar_id: str) -> dict:
        """
        :param angle: The angle in degrees.
        :param avatar_id: The ID of the avatar.

        :return: A `bend_arm_joint_by` command.
        """

        if self.left:
            joint = f"{self.joint_type.name}_left"
        else:
            joint = f"{self.joint_type.name}_right"

        return {"$type": "bend_arm_joint_by",
                "angle": angle,
                "joint": joint,
                "axis": self.axis.name,
                "avatar_id": avatar_id}

    def get_bend_to(self, angle: float, avatar_id: str) -> dict:
        """
        :param angle: The angle in degrees.
        :param avatar_id: The ID of the avatar.

        :return: A `bend_arm_joint_to` command.
        """

        if self.left:
            joint = f"{self.joint_type.name}_left"
        else:
            joint = f"{self.joint_type.name}_right"

        return {"$type": "bend_arm_joint_to",
                "angle": angle,
                "joint": joint,
                "axis": self.axis.name,
                "avatar_id": avatar_id}

    def get_stop(self, avatar_id: str) -> dict:
        """
        :param avatar_id: The ID of the avatar.

        :return: A `stop_arm_joint` command.
        """

        if self.left:
            joint = f"{self.joint_type.name}_left"
        else:
            joint = f"{self.joint_type.name}_right"

        return {"$type": "stop_arm_joint",
                "joint": joint,
                "axis": self.axis.name,
                "avatar_id": avatar_id}

    def __eq__(self, other):
        return isinstance(other, _Joint) and self.joint_type == other.joint_type and self.axis == other.axis

    def __hash__(self):
        return hash((self.joint_type, self.axis))


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


class BodyPartDynamic:
    """
    Dynamic (per-frame) data for a body part.
    """
    def __init__(self, b_id: int, avsm: AvatarStickyMitten):
        """
        :param b_id: The object ID.
        :param avsm: AvatarStickyMitten output data.
        """

        self.object_id = b_id

        tr_id = None
        ri_id = None
        for i in range(avsm.get_num_body_parts()):
            if avsm.get_body_part_id(i) == b_id:
                tr_id = i
            if avsm.get_rigidbody_part_id(i) == b_id:
                ri_id = i

        self.position = np.array(avsm.get_body_part_position(tr_id))
        self.rotation = np.array(avsm.get_body_part_rotation(tr_id))
        self.forward = np.array(avsm.get_body_part_forward(tr_id))

        # This is a rigidbody part.
        if ri_id is not None:
            self.velocity = np.array(avsm.get_rigidbody_part_velocity(ri_id))
            self.angular_velocity = np.array(avsm.get_rigidbody_part_angular_velocity(ri_id))
        else:
            self.velocity = None
            self.angular_velocity = None


class Avatar(Entity):
    """
    Wrapper function for creating an avatar and storing static data.
    """

    # Approximate length of arms.
    _ARM_LENGTH = {"baby": 0.52,
                   "adult": 1.16}

    # All valid avatar joints.
    _JOINTS = {Joint.shoulder_left_pitch: _Joint(joint_type=_JointType.shoulder, axis=_Axis.pitch, left=True),
               Joint.shoulder_left_yaw: _Joint(joint_type=_JointType.shoulder, axis=_Axis.yaw, left=True),
               Joint.shoulder_left_roll: _Joint(joint_type=_JointType.shoulder, axis=_Axis.roll, left=True),
               Joint.elbow_left_pitch: _Joint(joint_type=_JointType.elbow, axis=_Axis.pitch, left=True),
               Joint.wrist_left_pitch: _Joint(joint_type=_JointType.wrist, axis=_Axis.pitch, left=True),
               Joint.wrist_left_roll: _Joint(joint_type=_JointType.wrist, axis=_Axis.roll, left=True),
               Joint.shoulder_right_pitch: _Joint(joint_type=_JointType.shoulder, axis=_Axis.pitch, left=False),
               Joint.shoulder_right_yaw: _Joint(joint_type=_JointType.shoulder, axis=_Axis.yaw, left=False),
               Joint.shoulder_right_roll: _Joint(joint_type=_JointType.shoulder, axis=_Axis.roll, left=False),
               Joint.elbow_right_pitch: _Joint(joint_type=_JointType.elbow, axis=_Axis.pitch, left=False),
               Joint.wrist_right_pitch: _Joint(joint_type=_JointType.wrist, axis=_Axis.pitch, left=False),
               Joint.wrist_right_roll: _Joint(joint_type=_JointType.wrist, axis=_Axis.roll, left=False)}

    def __init__(self, c: Controller, avatar: str = "baby",
                 position: Dict[str, float] = None, avatar_id: str = "a"):
        """
        When this constructor is called, the controller `c` creates an avatar and steps forward 1 frame.

        :param c: The controller.
        :param avatar: The type of avatar. Options: `"baby"`, `"adult"`
        :param position: The initial position of the avatar. If `None`, the initial position is `(0, 0, 0)`.
        :param avatar_id: The ID of the avatar.
        """

        # Get the matching TDW enum.
        if avatar == "baby":
            at = "A_StickyMitten_Baby"
        elif avatar == "adult":
            at = "A_StickyMitten_Adult"
        else:
            raise Exception(f"Avatar type not found: {avatar}")
        self.avatar_id = avatar_id
        self.arm_length = Avatar._ARM_LENGTH[avatar]

        if position is None:
            position = {"x": 0, "y": 0, "z": 0}
        # Create the avatar.
        commands = TDWUtils.create_avatar(avatar_type=at, avatar_id=avatar_id, position=position)[:]
        # Request segmentation colors, body part names, and dynamic avatar data.
        # Turn off the follow camera.
        # Set the palms to sticky.
        commands.extend([{"$type": "send_avatar_segmentation_colors",
                          "frequency": "once",
                          "ids": [avatar_id]},
                         {"$type": "send_avatars",
                          "ids": [avatar_id],
                          "frequency": "always"},
                         {"$type": "toggle_image_sensor",
                          "sensor_name": "FollowCamera",
                          "avatar_id": avatar_id},
                         {"$type": "set_stickiness",
                          "sub_mitten": "palm",
                          "sticky": True,
                          "is_left": True,
                          "avatar_id": avatar_id},
                         {"$type": "set_stickiness",
                          "sub_mitten": "palm",
                          "sticky": True,
                          "is_left": False,
                          "avatar_id": avatar_id},
                         {"$type": "set_avatar_collision_detection_mode",
                          "mode": "continuous_dynamic",
                          "avatar_id": avatar_id},
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
        avsc = get_data(resp, AvatarStickyMittenSegmentationColors)

        # Cache static data of body parts.
        self.body_parts_static: Dict[str, BodyPartStatic] = dict()
        for i in range(avsc.get_num_body_parts()):
            bps = BodyPartStatic(o_id=avsc.get_body_part_id(i),
                                 color=avsc.get_body_part_segmentation_color(i))
            self.body_parts_static[avsc.get_body_part_name(i)] = bps

        # Start dynamic data.
        self.avsm = self._get_avsm(resp)

    def on_frame(self, resp: List[bytes]) -> None:
        # Update dynamic data.
        self.avsm = self._get_avsm(resp)

    @staticmethod
    def _get_avsm(resp: List[bytes]) -> AvatarStickyMitten:
        """
        :param resp: The response from the build.

        :return: AvatarStickyMitten output data.
        """

        return get_data(resp, AvatarStickyMitten)

    def get_dynamic_body_part(self, name: str) -> BodyPartDynamic:
        """
        :param name: The name of the part.

        :return: This frame's data for the body part.
        """

        if name not in self.body_parts_static:
            raise Exception(f"Body part undefined: {name}")
        return BodyPartDynamic(b_id=self.body_parts_static[name].o_id, avsm=self.avsm)

    def bend_arm_joints(self, c: Controller, movements: Dict[Joint, float],
                        frame_commands: Union[List[dict], dict] = None, by: bool = True) -> None:
        """
        Send commands to bend the arm joints. Wait until the joints stop moving.

        :param movements: A dictionary of joints. Key = The joint (see `sticky_mitten_avatar.Joint`). Value = the angle.
        :param frame_commands: Commands to send per-frame, if any.
        :param by: If True, send `bend_arm_joint_by` commands. If False, send `bend_arm_joint_to` commands.
        :param c: The controller.

        :return: A dictionary of collisions that occured while the joints moved. Key = frame.
        """

        # Convert movement dictionary to commands.
        commands = []
        for j in movements:
            if by:
                cmd = Avatar._JOINTS[j].get_bend_by(angle=movements[j], avatar_id=self.avatar_id)
            else:
                cmd = Avatar._JOINTS[j].get_bend_to(angle=movements[j], avatar_id=self.avatar_id)
            commands.append(cmd)

        if frame_commands is None:
            frame_commands = []

        # Do the commands.
        resp = c.communicate(commands)
        self.on_frame(resp=resp)

        # Get the body part rotations.
        body_part_rotations: Dict[int, np.array] = dict()
        for i in range(self.avsm.get_num_body_parts()):
            body_part_rotations[self.avsm.get_body_part_id(i)] = np.array(self.avsm.get_body_part_rotation(i))
        # Wait for the joints to stop rotating.
        done_rotating = False
        while not done_rotating:
            resp = c.communicate(frame_commands)
            self.on_frame(resp=resp)
            bpr: Dict[int, np.array] = dict()
            done_rotating = True
            for j in range(self.avsm.get_num_body_parts()):
                b_id = self.avsm.get_body_part_id(j)
                bpr[b_id] = np.array(self.avsm.get_body_part_rotation(j))
                if np.linalg.norm(bpr[b_id] - body_part_rotations[b_id]) > 0.001:
                    done_rotating = False

            body_part_rotations.clear()
            for b_id in bpr:
                body_part_rotations[b_id] = bpr[b_id]

    def stop_arms(self, c: Controller) -> None:
        """
        Stop all arm movement.

        :param c: The controller.
        """

        commands = []
        for j in Avatar._JOINTS:
            commands.append(Avatar._JOINTS[j].get_stop(self.avatar_id))
        c.communicate(commands)

    def drop_arms(self, c: Controller) -> None:
        """
        Set the joints to neutral (all angles are 0).

        :param c: The controller.
        """

        commands = []
        for j in Avatar._JOINTS:
            commands.append(Avatar._JOINTS[j].get_bend_to(avatar_id=self.avatar_id, angle=0))
        c.communicate(commands)

