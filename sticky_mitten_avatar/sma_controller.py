import numpy as np
from typing import Dict, List, Union
from tdw.controller import Controller
from tdw.tdw_utils import TDWUtils
from tdw.output_data import Bounds
from sticky_mitten_avatar.avatars import Arm, Baby
from sticky_mitten_avatar.avatars.avatar import Avatar
from sticky_mitten_avatar.util import get_data


class StickyMittenAvatarController(Controller):
    def __init__(self, port: int = 1071, launch_build: bool = True):
        # Cache the entities.
        self._avatars: Dict[str, Avatar] = dict()
        # Commands sent by avatars.
        self._avatar_commands: List[dict] = []

        super().__init__(port=port, launch_build=launch_build)

    def create_avatar(self, avatar_type: str = "baby", avatar_id: str = "a", position: Dict[str, float] = None,
                      debug: bool = False) -> None:
        """
        Create an avatar. Set default values for the avatar. Cache its static data (segmentation colors, etc.)

        :param avatar_type: The type of avatar. Options: "baby", "adult"
        :param avatar_id: The unique ID of the avatar.
        :param position: The initial position of the avatar.
        :param debug: If true, print debug messages when the avatar moves.
        """

        if avatar_type == "baby":
            avatar_type = "A_StickyMitten_Baby"
        elif avatar_type == "adult":
            avatar_type = "A_StickyMitten_Adult"
        else:
            raise Exception(f'Avatar type not found: {avatar_type}\nOptions: "baby", "adult"')

        if position is None:
            position = {"x": 0, "y": 0, "z": 0}

        commands = TDWUtils.create_avatar(avatar_type=avatar_type,
                                          avatar_id=avatar_id,
                                          position=position)[:]
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
                         {"$type": "set_avatar_drag",
                          "drag": 1000,
                          "angular_drag": 1000,
                          "avatar_id": avatar_id}])
        # Set the strength of the avatar.
        for joint in Avatar.JOINTS:
            commands.extend([{"$type": "adjust_joint_force_by",
                              "delta": 20,
                              "joint": joint.joint,
                              "axis": joint.axis,
                              "avatar_id": avatar_id},
                             {"$type": "adjust_joint_damper_by",
                              "delta": 200,
                              "joint": joint.joint,
                              "axis": joint.axis,
                              "avatar_id": avatar_id}])

        # Send the commands. Get a response.
        resp = self.communicate(commands)
        # Create the avatar.
        if avatar_type == "A_StickyMitten_Baby":
            avatar = Baby(avatar_id=avatar_id, debug=debug, resp=resp)
        else:
            raise Exception(f"Avatar not defined: {avatar_type}")
        # Cache the avatar.
        self._avatars[avatar_id] = avatar

    def communicate(self, commands: Union[dict, List[dict]]) -> list:
        if not isinstance(commands, list):
            commands = [commands]
        # Add avatar commands from the previous frame.
        commands.extend(self._avatar_commands[:])
        # Clear avatar commands.
        self._avatar_commands.clear()

        # Send the commands and get a response.
        resp = super().communicate(commands)

        # Update the avatars. Add new avatar commands for the next frame.
        for a_id in self._avatars:
            self._avatar_commands.extend(self._avatars[a_id].on_frame(resp=resp))
        return resp

    def bend_arm(self, avatar_id: str, arm: Arm, target: Union[np.array, list]) -> None:
        """
        Begin to bend an arm of an avatar in the scene. The motion will continue to update per `communicate()` step.

        :param arm: The arm (left or right).
        :param target: The target position for the mitten.
        :param avatar_id: The unique ID of the avatar.
        """

        self._avatar_commands.extend(self._avatars[avatar_id].bend_arm(arm=arm, target=target))

    def pick_up(self, avatar_id: str, arm: Arm, object_id: int) -> None:
        """
        Begin to bend an avatar's arm to try to pick up an object in the scene.
        The simulation will advance 1 frame (to collect the object's bounds data).
        The motion will continue to update per `communicate()` step.

        :param arm: The arm (left or right).
        :param object_id: The ID of the target object.
        :param avatar_id: The unique ID of the avatar.
        """

        # Get the bounds of the object.
        resp = self.communicate({"$type": "send_bounds",
                                 "frequency": "once",
                                 "ids": [object_id]})
        bounds = get_data(resp=resp, d_type=Bounds)
        self._avatar_commands.extend(self._avatars[avatar_id].pick_up(arm=arm, bounds=bounds, object_id=object_id))

    def put_down(self, avatar_id: str, reset_arms: bool = True) -> None:
        """
        Begin to put down all objects.
        The motion will continue to update per `communicate()` step.

        :param avatar_id: The unique ID of the avatar.
        :param reset_arms: If True, reset arm positions to "neutral".
        """

        self._avatar_commands.extend(self._avatars[avatar_id].put_down(reset_arms=reset_arms))

    def do_joint_motion(self) -> None:
        """
        Step through the simulation until the joints of all avatars are done moving.
        """

        done = False
        while not done:
            done = True
            # The loop is done if the IK goals are done.
            for avatar in self._avatars.values():
                if not avatar.is_ik_done():
                    done = False
            # Keep looping.
            if not done:
                self.communicate([])
