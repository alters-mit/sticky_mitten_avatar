from typing import Dict, Tuple, List
from tdw.tdw_utils import TDWUtils
from tdw.controller import Controller
from tdw.output_data import AvatarStickyMittenSegmentationColors, AvatarStickyMitten
from sticky_mitten_avatar.util import get_data


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


class Avatar:
    """
    Wrapper function for creating an avatar and storing static data.
    """

    def __init__(self, c: Controller, avatar: str = "baby",
                 position: Dict[str, float] = None, avatar_id: str = "a"):
        """
        When this constructor is called, the controller `c` creates an avatar and steps forward 1 frame.

        :param c: The controller.
        :param avatar: The type of avatar. Options: `"baby"`, `"adult"`
        :param position: The initial position of the avatar. If `None`, the initial position is `(0, 0, 0)`.
        :param avatar_id: The ID of the avatar.
        """

        if position is None:
            position = {"x": 0, "y": 0, "z": 0}

        # Get the matching TDW enum.
        if avatar == "baby":
            at = "A_StickyMitten_Baby"
        elif avatar == "adult":
            at = "A_StickyMitten_Adult"
        else:
            raise Exception(f"Avatar type not found: {avatar}")
        # Create the avatar.
        commands = TDWUtils.create_avatar(avatar_type=at, avatar_id=avatar_id, position=position)[:]
        # Request segmentation colors, body part names, and dynamic avatar data.
        # Turn off the follow camera.
        commands.extend([{"$type": "send_avatar_segmentation_colors",
                          "frequency": "once",
                          "ids": [avatar_id]},
                         {"$type": "send_avatars",
                          "ids": [avatar_id],
                          "frequency": "always"},
                         {"$type": "toggle_image_sensor",
                          "sensor_name": "FollowCamera",
                          "avatar_id": avatar_id}])
        # Send the commands. Get a response.
        resp = c.communicate(commands)
        avsc = get_data(resp, AvatarStickyMittenSegmentationColors)[0]

        # Cache static data of body parts.
        self.body_parts_static: Dict[int, BodyPartStatic] = dict()
        for i in range(avsc.get_num_body_parts()):
            self.body_parts_static[avsc.get_body_part_id(i)] = BodyPartStatic(avsc.get_body_part_id(i),
                                                                              avsc.get_body_part_segmentation_color(i))

        # Start dynamic data.
        self.avsm = get_data(resp, AvatarStickyMitten)[0]
