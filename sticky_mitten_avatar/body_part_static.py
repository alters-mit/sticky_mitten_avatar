from typing import Tuple
import numpy as np


class BodyPartStatic:
    """
    Static data for a body part in an avatar, such as a torso, an elbow, etc.

    ***

    ## Fields

    - `object_id` The object ID of the body part.
    - `segmentation_color` The segmentation color of the body part as a numpy array: `[r, b, b]`.
    - `name` The name of the body part.
    - `mass` The mass of the body part.

    ***

    ## Functions

    """

    def __init__(self, object_id: int, segmentation_color: Tuple[float, float, float], name: str, mass: float):
        """
        :param object_id: The object ID of the body part.
        :param segmentation_color: The segmentation color of the body part.
        :param name: The name of the body part.
        :param mass: The mass of the body part.
        """

        self.object_id = object_id
        self.segmentation_color = np.array(segmentation_color)
        self.name = name
        self.mass = mass
