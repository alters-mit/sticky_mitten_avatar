from typing import Dict, Tuple
from enum import Enum
from tdw.output_data import AvatarStickyMitten


class JointType(Enum):
    """
    The "type" of joint: The side, the joint, and the axis of rotation.
    """

    shoulder_left_pitch = 1,
    shoulder_left_yaw = 2,
    shoulder_left_roll = 4,
    elbow_left_pitch = 8,
    wrist_left_pitch = 16,
    wrist_left_roll = 32,
    shoulder_right_pitch = 64,
    shoulder_right_yaw = 128,
    shoulder_right_roll = 256,
    elbow_right_pitch = 512,
    wrist_right_pitch = 1024,
    wrist_right_roll = 2048


# The limits of each joint.
JOINT_LIMITS: Dict[JointType, Tuple[float, float]] = {JointType.shoulder_left_pitch: (-60, 179),
                                                      JointType.shoulder_left_yaw: (-90, 90),
                                                      JointType.shoulder_left_roll: (-45, 45),
                                                      JointType.elbow_left_pitch: (0, 160),
                                                      JointType.wrist_left_pitch: (0, 90),
                                                      JointType.wrist_left_roll: (-90, 90),
                                                      JointType.shoulder_right_pitch: (-60, 179),
                                                      JointType.shoulder_right_yaw: (-90, 90),
                                                      JointType.shoulder_right_roll: (-45, 45),
                                                      JointType.elbow_right_pitch: (0, 160),
                                                      JointType.wrist_right_pitch: (0, 90),
                                                      JointType.wrist_right_roll: (-90, 90)}


def get_joint_type(cmd: dict) -> JointType:
    """
    :param cmd: A bend-arm command.

    :return: The JointType associated with the command.
    """

    if cmd["$type"] != "bend_arm_joint_to" and cmd["$type"] != "bend_arm_joint_by":
        raise Exception(f"Not an arm-bending command: {cmd}")

    return JointType[f"{cmd['joint']}_{cmd['axis']}"]


def get_angles(avsm: AvatarStickyMitten) -> Dict[JointType, float]:
    """
    :param avsm: AvatarStickyMitten output data.

    :return: A dictionary of JointTypes mapped to current angles.
    """

    return {JointType.shoulder_left_pitch: avsm.get_angle_shoulder_left_pitch(),
            JointType.shoulder_left_yaw: avsm.get_angle_shoulder_left_yaw(),
            JointType.shoulder_left_roll: avsm.get_angle_shoulder_left_roll(),
            JointType.elbow_left_pitch: avsm.get_angle_elbow_left_pitch(),
            JointType.wrist_left_pitch: avsm.get_angle_wrist_left_pitch(),
            JointType.wrist_left_roll: avsm.get_angle_wrist_left_roll(),
            JointType.shoulder_right_pitch: avsm.get_angle_shoulder_right_pitch(),
            JointType.shoulder_right_yaw: avsm.get_angle_shoulder_right_yaw(),
            JointType.shoulder_right_roll: avsm.get_angle_shoulder_right_roll(),
            JointType.elbow_right_pitch: avsm.get_angle_elbow_right_pitch(),
            JointType.wrist_right_pitch: avsm.get_angle_wrist_right_pitch(),
            JointType.wrist_right_roll: avsm.get_angle_wrist_right_roll()}
