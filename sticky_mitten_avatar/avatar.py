from enum import Enum
import numpy as np
from typing import Dict, Tuple, List, Union
from tdw.tdw_utils import TDWUtils
from tdw.controller import Controller
from tdw.output_data import AvatarStickyMittenSegmentationColors, AvatarStickyMitten, Collision
from sticky_mitten_avatar.util import get_data, get_collisions
from sticky_mitten_avatar.entity import Entity


class Axis(Enum):
    """
    An axis of rotation.
    """

    pitch = 1,
    yaw = 2,
    roll = 4


class JointType(Enum):
    """
    A type of joint.
    """

    shoulder = 8,
    elbow = 16,
    wrist = 32


class Joint:
    """
    A type of joint an an axis.
    """

    def __init__(self, joint_type: JointType, axis: Axis, left: bool):
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

    def __eq__(self, other):
        return isinstance(other, Joint) and self.joint_type == other.joint_type and self.axis == other.axis

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

    def bend_arm_joints(self, c: Controller, commands: Union[List[dict], dict]) -> Dict[int, List[Collision]]:
        """
        Send commands to bend the arm joints. Wait until the joints stop moving.

        :param commands: The commands for this frame.
        :param c: The controller.

        :return: A dictionary of collisions that occured while the joints moved. Key = frame.
        """

        # Do the commands.
        resp = c.communicate(commands)
        self.on_frame(resp=resp)

        collisions: Dict[int, List[Collision]] = dict()
        collisions[c.get_frame(resp[-1])] = get_collisions(resp=resp)

        # Get the body part rotations.
        body_part_rotations: Dict[int, np.array] = dict()
        for i in range(self.avsm.get_num_body_parts()):
            body_part_rotations[self.avsm.get_body_part_id(i)] = np.array(self.avsm.get_body_part_rotation(i))
        # Wait for the joints to stop rotating.
        done_rotating = False
        while not done_rotating:
            resp = c.communicate([])
            collisions[c.get_frame(resp[-1])] = get_collisions(resp=resp)
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
        return collisions
