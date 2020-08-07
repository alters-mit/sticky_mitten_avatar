from typing import Union, Dict, Tuple
from enum import Enum
from tdw.tdw_utils import TDWUtils
from tdw.controller import Controller
from tdw.output_data import AvatarStickyMittenSegmentationColors
from sticky_mitten_avatar.util import get_data


class AvatarType(Enum):
    """
    A type of avatar. A baby avatar is much smaller than an adult.
    """
    baby = 1,
    adult = 2


class BodyPartStatic:
    """
    Static data for a body part in an avatar.
    """

    def __init__(self, o_id: int, color: Tuple[float, float, float]):
        """
        :param o_id: The object ID of the part.
        :param color: The color of the part.
        """

        self.o_id = o_id
        self.color = color


class Avatar:
    """
    Wrapper function for creating an avatar and storing static data.
    """

    def __init__(self, c: Controller, avatar: Union[AvatarType, str] = AvatarType.baby,
                 position: Dict[str, float] = None, avatar_id: str = "a"):
        if isinstance(avatar, str):
            if avatar == "baby":
                avatar = AvatarType.baby
            elif avatar == "adult":
                avatar = AvatarType.adult
            else:
                raise Exception(f"Avatar type not found: {avatar}")
        if position is None:
            position = {"x": 0, "y": 0, "z": 0}

        # Get the matching TDW enum.
        if avatar == AvatarType.baby:
            at = "A_StickyMitten_Baby"
        else:
            at = "A_StickyMitten_Adult"

        # Create the avatar.
        commands = TDWUtils.create_avatar(avatar_type=at, avatar_id=avatar_id, position=position)[:]
        # Request segmentation colors and body part names.
        # Turn off the follow camera.
        commands.extend([{"$type": "send_avatar_segmentation_colors",
                          "frequency": "once",
                          "ids": [avatar_id]},
                         {"$type": "toggle_image_sensor",
                          "sensor_name": "FollowCamera",
                          "avatar_id": avatar_id}])
        # Send the commands. Get a response.
        resp = c.communicate(commands)
        avsc = get_data(resp, AvatarStickyMittenSegmentationColors)[0]

        # Cache static data of body parts.
        self.body_parts: Dict[int, BodyPartStatic] = dict()
        for i in range(avsc.get_num_body_parts()):
            self.body_parts[avsc.get_body_part_id(i)] = BodyPartStatic(avsc.get_body_part_id(i),
                                                                       avsc.get_body_part_segmentation_color(i))
