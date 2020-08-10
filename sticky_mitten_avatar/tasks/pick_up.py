import numpy as np
from typing import Dict
from tdw.controller import Controller
from tdw.output_data import Bounds
from sticky_mitten_avatar.avatar import Avatar, Joint
from sticky_mitten_avatar.tasks import Task
from sticky_mitten_avatar.util import get_data, get_bounds_dict, get_angle


class PickUp(Task):
    """
    Bend the arm to move one of the mittens to the target object and try to pick it up.
    """

    def __init__(self, avatar: Avatar, object_id: int):
        """
        :param avatar: The avatar.
        :param object_id: The ID of the target object.
        """

        super().__init__(avatar=avatar)
        self.object_id = object_id
        self.left = False
        self.shoulder_pitch = Joint.shoulder_left_pitch
        self.shoulder_roll = Joint.shoulder_left_roll
        self.shoulder_yaw = Joint.shoulder_left_yaw
        self.elbow_pitch = Joint.elbow_left_pitch
        self.wrist_roll = Joint.wrist_left_roll

    def do(self, c: Controller) -> bool:
        # Get bounds data for the object.
        resp = c.communicate({"$type": "send_bounds",
                              "frequency": "once",
                              "ids": [self.object_id]})

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
            self.left = True
        else:
            mitten_name = "mitten_right"
            mitten = mitten_right
            self.left = False

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

        # Get the joints in the arm.
        if self.left:
            self.shoulder_pitch = Joint.shoulder_left_pitch
            self.shoulder_yaw = Joint.shoulder_left_yaw
            self.shoulder_roll = Joint.shoulder_left_roll
            self.elbow_pitch = Joint.elbow_left_pitch
            self.wrist_roll = Joint.wrist_left_roll
        else:
            self.shoulder_pitch = Joint.shoulder_right_pitch
            self.shoulder_yaw = Joint.shoulder_right_yaw
            self.shoulder_roll = Joint.shoulder_right_roll
            self.elbow_pitch = Joint.elbow_right_pitch
            self.wrist_roll = Joint.wrist_right_roll

        # Rotate the wrist.
        if self.try_to_pick_up(c=c, movements={self.wrist_roll: 45 * -1 if self.left else 1}):
            return True

        mitten = self.avatar.get_dynamic_body_part(mitten_name)
        angle = get_angle(origin=mitten.position, forward=mitten.forward, position=target_pos)
        if angle > 180:
            angle -= 360
        a0 = angle
        # Swing the shoulder out.
        do_shoulder_yaw = True
        while do_shoulder_yaw:
            if self.try_to_pick_up(c=c, movements={self.shoulder_yaw: 3 * 1 if self.left else -1}):
                return True
            mitten = self.avatar.get_dynamic_body_part(mitten_name)
            a1 = get_angle(origin=mitten.position, forward=mitten.forward, position=target_pos)
            if a1 > 180:
                a1 -= 360
            do_shoulder_yaw = (angle - a0) > (angle - a1)
            a0 = a1

        # Pitch the shoulder and the elbow.
        do_pitch = True
        while do_pitch:
            if self.try_to_pick_up(c=c, movements={self.shoulder_pitch: 3, self.elbow_pitch: 3}):
                return True
            mitten = self.avatar.get_dynamic_body_part(mitten_name)
            do_pitch = mitten.position[1] < object_bounds["top"][1] * 1.5

        # Swing the shoulder back in.
        if self.try_to_pick_up(c=c, movements={self.shoulder_yaw: -45 * 1 if self.left else -1}):
            return True

        # Failed to pick up the object.
        return False

    def end(self, c: Controller, success: bool) -> None:
        if success:
            # Raise the arm.
            self.avatar.bend_arm_joints(c=c, by=False,
                                        movements={self.shoulder_pitch: 25,
                                                   self.shoulder_yaw: 5 * 1 if self.left else -1,
                                                   self.elbow_pitch: 100,
                                                   self.shoulder_roll: -5 * -1 if self.left else 1,
                                                   self.wrist_roll: -90 * 1 if self.left else -1})
        else:
            self.avatar.drop_arms(c=c)

    def try_to_pick_up(self, c: Controller, movements: Dict[Joint, float]) -> bool:
        """
        Bend arm joints. Per-frame, try to pick up the object.

        :param c: The controller.
        :param movements: All arm joint movements.

        :return: True if the avatar picked up the object.
        """

        # Set the pick-up command.
        pick_up = [{"$type": "pick_up_proximity",
                    "distance": 0.1,
                    "radius": 0.1,
                    "grip": 1000,
                    "is_left": self.left,
                    "avatar_id": self.avatar.avatar_id}]
        self.avatar.bend_arm_joints(c=c, movements=movements, frame_commands=pick_up)
        return self.object_id in self.avatar.avsm.get_held_right() or self.object_id in self.avatar.avsm.get_held_left()
