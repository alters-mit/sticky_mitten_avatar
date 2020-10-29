import matplotlib.pyplot
from typing import Dict, Union, List, Optional
import numpy as np
from abc import ABC, abstractmethod
from ikpy.chain import Chain
from ikpy.utils import geometry
from enum import Enum
from tdw.output_data import OutputData, AvatarStickyMittenSegmentationColors, AvatarStickyMitten, Collision, \
    EnvironmentCollision
from tdw.tdw_utils import TDWUtils
from sticky_mitten_avatar.util import get_angle_between, rotate_point_around, FORWARD
from sticky_mitten_avatar.body_part_static import BodyPartStatic
from sticky_mitten_avatar.task_status import TaskStatus


class Arm(Enum):
    """
    The side that an arm is on.
    """

    left = 0,
    right = 1


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
        self.arm = arm

    def _key(self):
        return self.joint, self.axis, self.arm

    def __str__(self):
        return self.arm + " " + self.joint + " " + self.axis

    def __hash__(self):
        return hash(self._key())

    def __eq__(self, other):
        return isinstance(other, Joint) and self._key() == other._key()


class _IKGoal:
    """
    The goal of an IK action.
    """

    def __init__(self, target: Union[np.array, list] = None, pick_up_id: int = None,
                 stop_on_mitten_collision: bool = False, rotations: Dict[str, float] = None, precision: float = 0.05):
        """
        :param pick_up_id: If not None, the ID of the object to pick up.
        :param target: The target position of the mitten.
        :param stop_on_mitten_collision: If True, stop moving if the mitten collides with anything.
        :param rotations: The target rotations.
        :param precision: The distance threshold to the target position.
        """

        self.stop_on_mitten_collision = stop_on_mitten_collision
        self.rotations = rotations
        self.precision = precision

        self.moving_joints = Avatar.ANGLE_ORDER[:]

        self.pick_up_id = pick_up_id
        if target is not None and isinstance(target, list):
            self.target = np.array(target)
        else:
            self.target = target


class Avatar(ABC):
    """
    High-level API for a sticky mitten avatar.
    Do not use this class directly; it is an abstract class. Use the `Baby` class instead (a subclass of `Avatar`).

    Fields:

    - `id` The ID of the avatar.
    - `body_parts_static` Static body parts data. Key = the name of the part. See `BodyPartsStatic`
    - `frame` Dynamic info for the avatar on this frame, such as its position. See `tdw.output_data.AvatarStickyMitten`
    - `status` The current `TaskStatus` of the avatar.
    """

    JOINTS: List[Joint] = [Joint(arm="left", axis="pitch", part="shoulder"),
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

    ANGLE_ORDER = ["shoulder_pitch", "shoulder_yaw", "shoulder_roll", "elbow_pitch", "wrist_roll", "wrist_pitch"]

    _GRIP = 10000

    def __init__(self, resp: List[bytes], avatar_id: str = "a", debug: bool = False):
        """
        :param resp: The response from the build after creating the avatar.
        :param avatar_id: The ID of the avatar.
        :param debug: If True, print debug statements.
        """

        self.id = avatar_id
        self._debug = debug
        # Set the arm chains.
        self._arms: Dict[Arm, Chain] = {Arm.left: self._get_left_arm(),
                                        Arm.right: self._get_right_arm()}

        self._initial_mitten_positions = self._get_initial_mitten_positions()

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

        # Get data for the current frame.
        self.frame = self._get_frame(resp)
        # Get the masses of each body part.
        body_part_masses: Dict[int, float] = dict()
        for i in range(self.frame.get_num_rigidbody_parts()):
            body_part_masses[self.frame.get_rigidbody_part_id(i)] = self.frame.get_rigidbody_part_mass(i)

        # Cache static data of body parts.
        self.body_parts_static: Dict[int, BodyPartStatic] = dict()
        self.base_id = 0
        self.mitten_ids: Dict[Arm, int] = dict()
        for i in range(smsc.get_num_body_parts()):
            body_part_id = smsc.get_body_part_id(i)
            if body_part_id in body_part_masses:
                mass = body_part_masses[body_part_id]
            else:
                mass = 0.1
            name = smsc.get_body_part_name(i)
            # Cache the base ID and the mitten IDs.
            if name.startswith("A_StickyMitten"):
                self.base_id = body_part_id
            elif name == "mitten_left":
                self.mitten_ids[Arm.left] = body_part_id
            elif name == "mitten_right":
                self.mitten_ids[Arm.right] = body_part_id
            bps = BodyPartStatic(object_id=body_part_id,
                                 segmentation_color=smsc.get_body_part_segmentation_color(i),
                                 name=name,
                                 mass=mass)
            self.body_parts_static[body_part_id] = bps

        # Start dynamic data.
        self.collisions: Dict[int, List[int]] = dict()
        self.env_collisions: List[int] = list()

        self.status = TaskStatus.idle

        self._mass = self._get_mass()

    def can_reach_target(self, target: np.array, arm: Arm) -> TaskStatus:
        """
        :param target: The target position.
        :param arm: The arm that is bending to the target.

        :return: A `TaskResult` value describing whether the avatar can reach the target and, if not, why.
        """

        pos = np.array([target[0], target[2]])
        d = np.linalg.norm(pos)
        if d < 0.2:
            if self._debug:
                print(f"Target {target} is too close to the avatar: {np.linalg.norm(d)}")
            return TaskStatus.too_close_to_reach
        if target[2] < 0:
            if self._debug:
                print(f"Target {target} is behind avatar.")
            return TaskStatus.behind_avatar

        # Check if the IK solution reaches the target.
        chain = self._arms[arm]
        joints, ik_target = self._get_ik(target=target, arm=arm)
        transformation_matrixes = chain.forward_kinematics(list(joints), full_kinematics=True)
        nodes = []
        for (index, link) in enumerate(chain.links):
            (node, orientation) = geometry.from_transformation_matrix(transformation_matrixes[index])
            nodes.append(node)
        destination = np.array(nodes[-1][:-1])

        # Check if any node is likely to enter the body.
        for node, link in zip(nodes[4:], chain.links[4:]):
            d = np.linalg.norm(np.array([node[0], node[2]]))
            # If this is a short distance and the node is below head-level, then this is likely to intersect.
            if d < 0.1 and node[1] < 1:
                if self._debug:
                    print(f"Target {target} is too close to a joint: {d}, {node}, {link.name}")
                return TaskStatus.too_close_to_reach

        d = np.linalg.norm(destination - target)
        if d > 0.125:
            if self._debug:
                print(f"Target {target} is too far away from {arm}: {d}")
            return TaskStatus.too_far_to_reach
        return TaskStatus.success

    def reach_for_target(self, arm: Arm, target: np.array, stop_on_mitten_collision: bool,
                         target_orientation: np.array = None, precision: float = 0.05) -> List[dict]:
        """
        Get an IK solution to move a mitten to a target position.

        :param arm: The arm (left or right).
        :param target: The target position for the mitten.
        :param target_orientation: Target IK orientation. Usually you should leave this as None (the default).
        :param stop_on_mitten_collision: If true, stop moving when the mitten collides with something.
        :param precision: The distance threshold to the target position.

        :return: A list of commands to begin bending the arm.
        """

        # Get the IK solution.
        rotations, ik_target = self._get_ik(target=target, arm=arm, target_orientation=target_orientation)

        angle = get_angle_between(v1=FORWARD, v2=self.frame.get_forward())
        target = rotate_point_around(point=ik_target, angle=angle) + self.frame.get_position()

        rotation_targets = dict()
        for c, r in zip(self._arms[arm].links[1:-1], rotations[1:-1]):
            rotation_targets[c.name] = r

        self._ik_goals[arm] = _IKGoal(target=target, stop_on_mitten_collision=stop_on_mitten_collision,
                                      rotations=rotation_targets, precision=precision)

        commands = [self.get_start_bend_sticky_mitten_profile(arm=arm)]

        # If the avatar is holding something, strengthen the wrist.
        held = self.frame.get_held_left() if arm == Arm.left else self.frame.get_held_right()
        if len(held) > 0:
            commands.append({"$type": "set_joint_angular_drag",
                             "joint": f"wrist_{arm.name}",
                             "axis": "roll",
                             "angular_drag": 50,
                             "avatar_id": self.id})
        if self._debug:
            print([np.rad2deg(r) for r in rotations])
            self._plot_ik(target=ik_target, arm=arm)

            # Show the target.
            commands.extend([{"$type": "remove_position_markers"},
                             {"$type": "add_position_marker",
                              "position": TDWUtils.array_to_vector3(target)}])
        a = arm.name
        for c in self._ik_goals[arm].rotations:
            j = c.split("_")
            # Apply the motion.
            commands.extend([{"$type": "bend_arm_joint_to",
                              "angle": np.rad2deg(self._ik_goals[arm].rotations[c]),
                              "joint": f"{j[0]}_{a}",
                              "axis": j[1],
                              "avatar_id": self.id}])
        return commands

    def grasp_object(self, object_id: int, target: np.array, arm: Arm, stop_on_mitten_collision: bool) -> List[dict]:
        """
        Begin to try to grasp an object with a mitten. Get an IK solution to a target position.

        :param object_id: The ID of the target object.
        :param target: Target position to for the IK solution.
        :param arm: The arm that will try to grasp the object.
        :param stop_on_mitten_collision: If true, stop moving when the mitten collides with something.

        :return: A list of commands.
        """

        # Get the mitten's position.
        if arm == Arm.left:
            mitten = np.array(self.frame.get_mitten_center_left_position())
        else:
            mitten = np.array(self.frame.get_mitten_center_right_position())

        target_orientation = (mitten - target) / np.linalg.norm(mitten - target)

        target = self.get_rotated_target(target=target)

        commands = self.reach_for_target(arm=arm, target=target, target_orientation=target_orientation,
                                         stop_on_mitten_collision=stop_on_mitten_collision)
        self._ik_goals[arm].pick_up_id = object_id
        return commands

    def on_frame(self, resp: List[bytes]) -> List[dict]:
        """
        Update the avatar based on its current arm-bending goals and its state.
        If the avatar has achieved a goal (for example, picking up an object), it will stop moving that arm.
        Update the avatar's state as needed.

        :param resp: The response from the build.

        :return: A list of commands to pick up, stop moving, etc.
        """

        def _get_mitten_position(a: Arm) -> np.array:
            """
            :param a: The arm.

            :return: The position of a mitten.
            """

            if a == Arm.left:
                return np.array(frame.get_mitten_center_left_position())
            else:
                return np.array(frame.get_mitten_center_right_position())

        # Update dynamic data.
        frame = self._get_frame(resp=resp)
        # Update dynamic collision data.
        self.collisions.clear()
        self.env_collisions.clear()
        # Get each collision.
        for i in range(len(resp) - 1):
            r_id = OutputData.get_data_type_id(resp[i])
            if r_id == "coll":
                coll = Collision(resp[i])
                collider_id = coll.get_collider_id()
                collidee_id = coll.get_collidee_id()
                # Check if this was a mitten, if we're supposed to stop if there's a collision,
                # and if the collision was not with the target.
                for arm in self._ik_goals:
                    if self._ik_goals[arm] is not None:
                        if (collider_id == self.mitten_ids[arm] or collidee_id == self.mitten_ids[arm]) and \
                                (collider_id not in frame.get_held_right() and
                                 collider_id not in frame.get_held_left() and
                                 collidee_id not in frame.get_held_right() and
                                 collidee_id not in frame.get_held_left()) and \
                                self._ik_goals[arm].stop_on_mitten_collision and \
                                (self._ik_goals[arm].target is None or
                                 (self._ik_goals[arm].pick_up_id != collidee_id and
                                  self._ik_goals[arm].pick_up_id != collider_id)) and \
                                (collidee_id not in self.body_parts_static or
                                 collider_id not in self.body_parts_static):
                            self.status = TaskStatus.mitten_collision
                            self._ik_goals[arm] = None
                            if self._debug:
                                print("Stopping because the mitten collided with something.")
                            return self._stop_arm(arm=arm)
                # Check if the collision includes a body part.
                if collider_id in self.body_parts_static and collidee_id not in self.body_parts_static:
                    if collider_id not in self.collisions:
                        self.collisions[collider_id] = []
                    self.collisions[collider_id].append(collidee_id)
                elif collidee_id in self.body_parts_static and collider_id not in self.body_parts_static:
                    if collidee_id not in self.collisions:
                        self.collisions[collidee_id] = []
                    self.collisions[collidee_id].append(collider_id)
            elif r_id == "enco":
                coll = EnvironmentCollision(resp[i])
                collider_id = coll.get_object_id()
                if collider_id in self.body_parts_static:
                    self.env_collisions.append(collider_id)

        # Check if IK goals are done.
        temp_goals: Dict[Arm, Optional[_IKGoal]] = dict()
        # Get commands for the next frame.
        commands: List[dict] = []
        for arm in self._ik_goals:
            # No IK goal on this arm.
            if self._ik_goals[arm] is None:
                temp_goals[arm] = None
            # This is a dummy IK goal. Let it run.
            elif self._ik_goals[arm].target is None:
                temp_goals[arm] = self._ik_goals[arm]
            else:
                # Is the arm at the target?
                mitten_position = _get_mitten_position(arm)
                # If we're not trying to pick something up, check if we are at the target position.
                if self._ik_goals[arm].pick_up_id is None:
                    # If we're at the position, stop.
                    d = np.linalg.norm(mitten_position - self._ik_goals[arm].target)
                    if d < self._ik_goals[arm].precision:
                        if self._debug:
                            print(f"{arm.name} mitten is at target position {self._ik_goals[arm].target}. Stopping.")
                        commands.extend(self._stop_arm(arm=arm))
                        temp_goals[arm] = None
                        self.status = TaskStatus.success
                    # Keep bending the arm.
                    else:
                        temp_goals[arm] = self._ik_goals[arm]
                        self._ik_goals[arm].previous_distance = d
                # If we're trying to pick something, check if it was picked up on the previous frame.
                else:
                    if self._ik_goals[arm].pick_up_id in frame.get_held_left() or self._ik_goals[arm]. \
                            pick_up_id in frame.get_held_right():
                        if self._debug:
                            print(f"{arm.name} mitten picked up {self._ik_goals[arm].pick_up_id}. Stopping.")
                        commands.extend(self._stop_arm(arm=arm))
                        temp_goals[arm] = None
                        self.status = TaskStatus.success
                    # Keep bending the arm and trying to pick up the object.
                    else:
                        commands.extend([{"$type": "pick_up_proximity",
                                          "distance": 0.02,
                                          "radius": 0.05,
                                          "grip": 1000,
                                          "is_left": arm == Arm.left,
                                          "avatar_id": self.id,
                                          "object_ids": [self._ik_goals[arm].pick_up_id]},
                                         {"$type": "pick_up",
                                          "grip": 1000,
                                          "is_left": arm == Arm.left,
                                          "object_ids": [self._ik_goals[arm].pick_up_id],
                                          "avatar_id": self.id}])
                        temp_goals[arm] = self._ik_goals[arm]

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
                # Try to stop any moving joints.
                if self._ik_goals[arm].rotations is not None and self._ik_goals[arm].pick_up_id is not None:
                    joint_profile = self._get_default_sticky_mitten_profile()
                    for angle, joint_name in zip(angles_1, Avatar.ANGLE_ORDER):
                        target_angle = self._ik_goals[arm].rotations[joint_name]
                        # Check if the joint stopped moving. Ignore if the joint already stopped.
                        if target_angle > 0.01 and np.abs(angle - target_angle) < 0.01 and \
                                joint_name in self._ik_goals[arm].moving_joints:
                            self._ik_goals[arm].moving_joints.remove(joint_name)
                            j = joint_name.split("_")
                            j_name = f"{j[0]}_{arm.name}"
                            axis = j[1]
                            # Set the name of the elbow to the expected profile key.
                            if "elbow" in joint_name:
                                profile_key = "elbow"
                            else:
                                profile_key = joint_name
                            if self._debug:
                                print(f"{joint_name} {arm.name} slowing down: {np.abs(angle - target_angle)}")
                            # Stop the joint from moving any more.
                            # Set the damper, force, and angular drag to "default" (non-moving) values.
                            commands.extend([{"$type": "set_joint_damper",
                                              "joint": j_name,
                                              "axis": axis,
                                              "damper": joint_profile[profile_key]["damper"],
                                              "avatar_id": self.id},
                                             {"$type": "set_joint_force",
                                              "joint": j_name,
                                              "axis": axis,
                                              "force": joint_profile[profile_key]["force"],
                                              "avatar_id": self.id},
                                             {"$type": "set_joint_angular_drag",
                                              "joint": j_name,
                                              "axis": axis,
                                              "angular_drag": joint_profile[profile_key]["angular_drag"],
                                              "avatar_id": self.id}])
                # Is any joint still moving?
                moving = False
                for a0, a1 in zip(angles_0, angles_1):
                    if np.abs(a0 - a1) > 0.03:
                        moving = True
                        break
                # Keep moving.
                if moving:
                    temp_goals[arm] = self._ik_goals[arm]
                else:
                    if self._ik_goals[arm].rotations is not None:
                        # This is a reset arm action.
                        if self._ik_goals[arm].target is None:
                            mitten_position = _get_mitten_position(arm) - frame.get_position()
                            d = np.linalg.norm(self._initial_mitten_positions[arm] - mitten_position)
                            # The reset arm action ended with the mitten very close to the initial position.
                            if d < self._ik_goals[arm].precision:
                                self.status = TaskStatus.success
                            else:
                                self.status = TaskStatus.no_longer_bending
                        # This is a regular action.
                        # It ended with the arm no longer moving but having never reached the target.
                        else:
                            if self._debug:
                                print(f"{arm.name} is no longer bending. Cancelling.")
                            self.status = TaskStatus.no_longer_bending
                        commands.extend(self._stop_arm(arm=arm))
                    temp_goals[arm] = None
        self._ik_goals = temp_goals
        self.frame = frame

        return commands

    def is_ik_done(self) -> bool:
        """
        :return: True if the IK goals are complete, False if the arms are still moving/trying to pick up/etc.
        """

        return self._ik_goals[Arm.left] is None and self._ik_goals[Arm.right] is None

    def drop(self, arm: Arm, reset: bool = True) -> List[dict]:
        """
        Drop all objects held by an arm.

        :param arm: The arm that will drop all held objects.
        :param reset: If True, reset the arm's positions to "neutral".

        :return: A list of commands to put down the object.
        """

        commands = [self.get_default_sticky_mitten_profile(),
                    {"$type": "put_down",
                     "is_left": True if arm == Arm.left else False,
                     "avatar_id": self.id}]
        if reset:
            commands.extend(self.reset_arm(arm=arm))
        return commands

    def reset_arm(self, arm: Arm) -> List[dict]:
        """
        :param arm: The arm that will be reset.

        :return: A list of commands to drop arms to their starting positions.
        """

        commands = [self.get_reset_arm_sticky_mitten_profile(arm=arm)]
        for j in self.JOINTS:
            if j.arm != arm.name:
                continue
            commands.append({"$type": "bend_arm_joint_to",
                             "joint": j.joint,
                             "axis": j.axis,
                             "angle": 0,
                             "avatar_id": self.id})

        rotations = dict()
        for c in self._arms[arm].links[1:-1]:
            rotations[c.name] = 0
        # Set the IK goal.
        self._ik_goals[arm] = _IKGoal(rotations=rotations, precision=0.1)
        return commands

    def is_holding(self, object_id: int) -> (bool, Arm):
        """
        :param object_id: The ID of the object.

        :return: True if the avatar is holding the object and, if so, the arm holding the object.
        """

        if object_id in self.frame.get_held_left():
            return True, Arm.left
        elif object_id in self.frame.get_held_right():
            return True, Arm.right
        return False, Arm.left

    def _stop_arm(self, arm: Arm) -> List[dict]:
        """
        :param arm: The arm to stop.

        :return: Commands to stop all the arm from moving.
        """

        if arm == Arm.left:
            joints = Avatar.JOINTS[:6]
            angles = self.frame.get_angles_left()
        else:
            joints = Avatar.JOINTS[6:]
            angles = self.frame.get_angles_right()

        commands = [self.get_default_sticky_mitten_profile()]
        # Get the current angle and bend the joint to that angle.
        for j, a in zip(joints, angles):
            theta = float(a)
            if theta > 90:
                theta = 180 - theta
            # Set the joint positions to where they are.
            # Reset force and damper.
            commands.extend([{"$type": "bend_arm_joint_to",
                              "angle": theta,
                              "joint": j.joint,
                              "axis": j.axis,
                              "avatar_id": self.id}])
        return commands

    @abstractmethod
    def _get_left_arm(self) -> Chain:
        """
        :return: The IK chain of the left arm.
        """

        raise Exception()

    def _get_right_arm(self) -> Chain:
        """
        :return: The IK chain of the right arm.
        """

        raise Exception()

    def _get_frame(self, resp: List[bytes]) -> AvatarStickyMitten:
        """
        :param resp: The response from the build.

        :return: AvatarStickyMitten output data for this avatar on this frame.
        """
        for i in range(len(resp) - 1):
            r_id = OutputData.get_data_type_id(resp[i])
            if r_id == "avsm":
                avsm = AvatarStickyMitten(resp[i])
                if avsm.get_avatar_id() == self.id:
                    return avsm
        raise Exception(f"No avatar data found for {self.id}")

    def get_rotated_target(self, target: np.array) -> np.array:
        """
        Rotate the target by the avatar's forward directional vector.

        :param target: The target position.
        :return: The rotated position.
        """
        angle = get_angle_between(v1=FORWARD, v2=self.frame.get_forward())

        return rotate_point_around(point=target - self.frame.get_position(), angle=-angle)

    def _plot_ik(self, target: np.array, arm: Arm) -> None:
        """
        Debug an IK solution by creating a plot.

        :param target: The target position.
        :param arm: The arm.
        """

        chain = self._arms[arm]

        ax = matplotlib.pyplot.figure().add_subplot(111, projection='3d')

        chain.plot(chain.inverse_kinematics(target_position=target), ax, target=target)
        matplotlib.pyplot.show()

    def _get_ik(self, target: np.array, arm: Arm, target_orientation: np.array = None) -> (List[float], np.array):
        """
        :param target: The target position.
        :param arm: The arm.
        :param target_orientation: The target orientation. Can be None.

        :return: The IK angles and the IK target.
        """

        ik_target = np.array(target)

        # Get the IK solution.
        rotations = self._arms[arm].inverse_kinematics(target_position=ik_target, target_orientation=target_orientation)
        return rotations, ik_target

    @abstractmethod
    def _get_default_sticky_mitten_profile(self) -> dict:
        """
        :return: The default StickyMittenProfile of the joints.
        """

        raise Exception()

    @abstractmethod
    def _get_movement_sticky_mitten_profile(self) -> dict:
        """
        :return: The StickyMittenProfile for when the avatar is moving.
        """

        raise Exception()

    @abstractmethod
    def _get_start_bend_sticky_mitten_profile(self) -> dict:
        """
        :return: The StickyMittenProfile required for beginning to bend an arm.
        """

        raise Exception()

    @abstractmethod
    def _get_reset_arm_sticky_mitten_profile(self) -> dict:
        """
        :return: The StickyMittenProfile required for beginning to reset an arm.
        """

        raise Exception()

    @abstractmethod
    def _get_roll_wrist_sticky_mitten_profile(self) -> dict:
        """
        :return: The StickyMittenProfile required for beginning to roll a wrist.
        """

        raise Exception()

    def _get_mass(self) -> float:
        """
        :return: The mass of the avatar.
        """

        raise Exception()

    def _get_sticky_mitten_profile(self, left: dict, right: dict) -> dict:
        """
        :param left: Joint values for the left arm.
        :param right: Joint values for the right arm.

        :return: A `set_sticky_mitten_profile` command.
        """

        return {"$type": "set_sticky_mitten_profile",
                "profile": {"mass": self._mass,
                            "arm_left": left,
                            "arm_right": right,
                            "avatar_id": self.id}}

    def get_default_sticky_mitten_profile(self) -> dict:
        """
        :return: A `set_sticky_mitten_profile` command for the default joint values.
        """

        profile = self._get_default_sticky_mitten_profile()

        return self._get_sticky_mitten_profile(left=profile, right=profile)

    def get_start_bend_sticky_mitten_profile(self, arm: Arm) -> dict:
        """
        :param arm: The arm that is bending.

        :return: A `set_sticky_mitten_profile` command for beginning an arm-bending action.
        """

        # The profile for the moving arm.
        move = self._get_start_bend_sticky_mitten_profile()
        # The profile for the stopping arm.
        fixed = self._get_default_sticky_mitten_profile()

        return self._get_sticky_mitten_profile(left=move if arm == Arm.left else fixed,
                                               right=move if arm == Arm.right else fixed)

    def get_movement_sticky_mitten_profile(self) -> dict:
        """
        :return: A `set_sticky_mitten_profile` command for when the avatar needs to move.
        """

        move = self._get_movement_sticky_mitten_profile()

        return self._get_sticky_mitten_profile(left=move, right=move)

    def get_reset_arm_sticky_mitten_profile(self, arm: Arm) -> dict:
        """
        :param arm: The arm that is resetting.

        :return: A `set_sticky_mitten_profile` command for beginning an arm-reset action.
        """

        # The profile for the moving arm.
        move = self._get_reset_arm_sticky_mitten_profile()
        # The profile for the stopping arm.
        fixed = self._get_default_sticky_mitten_profile()

        return self._get_sticky_mitten_profile(left=move if arm == Arm.left else fixed,
                                               right=move if arm == Arm.right else fixed)

    def get_roll_wrist_sticky_mitten_profile(self, arm: Arm) -> dict:
        """
        :param arm: The arm that is resetting.

        :return: A `set_sticky_mitten_profile` command for beginning to roll a wrist.
        """

        # The profile for the moving arm.
        move = self._get_roll_wrist_sticky_mitten_profile()
        # The profile for the stopping arm.
        fixed = self._get_default_sticky_mitten_profile()

        return self._get_sticky_mitten_profile(left=move if arm == Arm.left else fixed,
                                               right=move if arm == Arm.right else fixed)

    @abstractmethod
    def _get_initial_mitten_positions(self) -> Dict[Arm, np.array]:
        """
        :return: The initial positions of each mitten relative to the avatar.
        """

        raise Exception()
