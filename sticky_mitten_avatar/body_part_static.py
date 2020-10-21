from typing import Tuple
from tdw.py_impact import ObjectInfo, AudioMaterial


class BodyPartStatic:
    """
    Static data for a body part in an avatar.

    Fields:

    - `object_id` The object ID of the body part.
    - `segmentation_color` The segmentation color of the body part.
    - `name` The name of the body part.
    - `audio` [Audio values](https://github.com/threedworld-mit/tdw/blob/master/Documentation/python/py_impact.md#objectinfo) for the body part.
    """

    def __init__(self, object_id: int, segmentation_color: Tuple[float, float, float], name: str, mass: float):
        """
        :param object_id: The object ID of the body part.
        :param segmentation_color: The segmentation color of the body part.
        :param name: The name of the body part.
        :param mass: The mass of the body part.
        """

        self.object_id = object_id
        self.segmentation_color = segmentation_color
        self.name = name
        self.audio = ObjectInfo(name=self.name, amp=0.01, mass=mass, material=AudioMaterial.ceramic, library="",
                                bounciness=0.1, resonance=0.5)
