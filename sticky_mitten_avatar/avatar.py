import numpy as np
from typing import Dict, Tuple, List
from tdw.tdw_utils import TDWUtils
from tdw.controller import Controller
from tdw.output_data import AvatarStickyMittenSegmentationColors, AvatarStickyMitten
from sticky_mitten_avatar.util import get_data
from sticky_mitten_avatar.entity import Entity


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
                          "avatar_id": avatar_id}])
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
