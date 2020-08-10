import numpy as np
from typing import List, Dict
from tdw.controller import Controller
from tdw.output_data import Bounds, Collision
from sticky_mitten_avatar.avatar import Avatar, JointType, Axis, Joint
from sticky_mitten_avatar.tasks import Task
from sticky_mitten_avatar.util import get_data, get_bounds_dict, get_angle


class PickUp(Task):
    """
    Bend the arm to move one of the mittens to the target object and try to pick it up.
    """

    def __init__(self, avatar: Avatar, target_id: int):
        """
        :param avatar: The avatar.
        :param target_id: The ID of the target object.
        """

        super().__init__(avatar=avatar)
        self.target_id = target_id

    def do(self, c: Controller) -> bool:
        # Get bounds data for the object.
        resp = c.communicate({"$type": "send_bounds",
                              "frequency": "once",
                              "ids": [self.target_id]})

        a_pos = np.array(self.avatar.avsm.get_position())
        a_for = np.array(self.avatar.avsm.get_forward())

        object_bounds = get_bounds_dict(bounds=get_data(resp=resp, d_type=Bounds), index=0)

        # If the object is too far away, immediately fail.
        if np.linalg.norm(a_pos - object_bounds["bottom"]) > self.avatar.arm_length:
            return False

        mitten_left = self.avatar.get_dynamic_body_part("mitten_left")
        mitten_right = self.avatar.get_dynamic_body_part("mitten_right")
        # Use the closer mitten.
        d_left = np.linalg.norm(mitten_left.position - object_bounds["bottom"])
        d_right = np.linalg.norm(mitten_right.position - object_bounds["bottom"])
        if d_left < d_right:
            mitten_name = "mitten_left"
            mitten = mitten_left
            left = True
            wrist_roll_direction = -1
            shoulder_yaw_direction = 1
        else:
            mitten_name = "mitten_right"
            mitten = mitten_right
            left = False
            wrist_roll_direction = 1
            shoulder_yaw_direction = -1

        # Get the position on the bounds at the greatest angle from the mitten.
        target_bounds_pos = ""
        target_bounds_angle = 0
        for bounds_pos in object_bounds:
            q = np.array([object_bounds[bounds_pos][0], 0, object_bounds[bounds_pos][2]])
            angle = get_angle(origin=mitten.position, forward=a_for, position=q)
            if angle > target_bounds_angle:
                target_bounds_angle = angle
                target_bounds_pos = bounds_pos
        target_pos = object_bounds[target_bounds_pos]

        # Rotate the wrist.
        wrist_roll = Joint(joint_type=JointType.wrist, axis=Axis.roll, left=left)
        self._apply_movement(movement={wrist_roll: 45 * wrist_roll_direction},
                             c=c)
        mitten = self.avatar.get_dynamic_body_part(mitten_name)
        angle = get_angle(origin=mitten.position, forward=mitten.forward, position=target_pos)
        if angle > 180:
            angle -= 360
        a0 = angle
        # Swing the shoulder out.
        do_shoulder_yaw = True
        shoulder_yaw = Joint(joint_type=JointType.shoulder, axis=Axis.yaw, left=left)
        while do_shoulder_yaw:
            self._apply_movement(movement={shoulder_yaw: 3 * shoulder_yaw_direction}, c=c)
            mitten = self.avatar.get_dynamic_body_part(mitten_name)
            a1 = get_angle(origin=mitten.position, forward=mitten.forward, position=target_pos)
            if a1 > 180:
                a1 -= 360
            do_shoulder_yaw = (angle - a0) > (angle - a1)
            a0 = a1

        # Pitch the shoulder and the elbow. Try to get closer.
        elbow_pitch = Joint(joint_type=JointType.elbow, axis=Axis.pitch, left=left)
        shoulder_pitch = Joint(joint_type=JointType.shoulder, axis=Axis.pitch, left=left)
        movement = {shoulder_pitch: 3,
                    elbow_pitch: 3}
        do_pitch = True
        while do_pitch:
            self._apply_movement(movement=movement, c=c)
            mitten = self.avatar.get_dynamic_body_part(mitten_name)
            do_pitch = mitten.position[1] < object_bounds["top"][1] * 1.5

        # Swing the shoulder back in.
        do_shoulder_yaw = True
        while do_shoulder_yaw:
            collisions = self._apply_movement(movement={shoulder_yaw: -1 * shoulder_yaw_direction}, c=c)
            # If the mitten touches the object, stop moving.
            for colls in collisions.values():
                for coll in colls:
                    if (self.target_id == coll.get_collidee_id() and mitten.object_id == coll.get_collider_id()) or\
                            (self.target_id == coll.get_collider_id() and mitten.object_id == coll.get_collidee_id()):
                        do_shoulder_yaw = False
                        break
        # Pick up the object.
        c.communicate({"$type": "pick_up_proximity",
                       "distance": 0.3,
                       "radius": 0.3,
                       "grip": 1000,
                       "is_left": left,
                       "avatar_id": self.avatar.avatar_id})
        if self.target_id not in self.avatar.avsm.get_held_right() and \
                self.target_id not in self.avatar.avsm.get_held_left():
            return False
        # Bring the arm and the object up.
        shoulder_roll = Joint(joint_type=JointType.shoulder, axis=Axis.roll, left=left)
        self._apply_movement(movement={shoulder_pitch: 25,
                                       shoulder_yaw: 5 * shoulder_yaw_direction,
                                       elbow_pitch: 100,
                                       shoulder_roll: -5 * wrist_roll_direction,
                                       wrist_roll: 90 * wrist_roll_direction},
                             c=c,
                             by=False)
        return True

    def end(self, c: Controller, success: bool) -> None:
        pass

    def _apply_movement(self, movement: Dict[Joint, float], c: Controller, by: bool = True) -> \
            Dict[int, List[Collision]]:
        """
        Convert a dictionary of movements to a series of commands and send it to the build.

        :param movement: Movements. Key = the joint type, axis, and side (left or right). Value = angle.
        :param c: The controller.
        :param by: If True, send bend_arm_joint_by commands. If False, send bend_arm_joint_to commands.

        :return: All collisions that occurred while the arms were bending.
        """

        commands = []
        for j in movement:
            if by:
                cmd = j.get_bend_by(angle=movement[j], avatar_id=self.avatar.avatar_id)
            else:
                cmd = j.get_bend_to(angle=movement[j], avatar_id=self.avatar.avatar_id)
            commands.append(cmd)
        return self.avatar.bend_arm_joints(c=c, commands=commands)
