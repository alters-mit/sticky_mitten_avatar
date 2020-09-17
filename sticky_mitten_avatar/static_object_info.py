import numpy as np
from tdw.output_data import SegmentationColors,Rigidbodies
from tdw.py_impact import ObjectInfo


class StaticObjectInfo:
    """
    Info for an object that doesn't change between frames.

    Fields:

    - `object_id`: The unique ID of the object.
    - `mass`: The mass of the object.
    - `segmentation_color`: The RGB segmentation color for the object as a numpy array.
    - `model_name`: [The name of the model.](https://github.com/threedworld-mit/tdw/blob/master/Documentation/python/librarian/model_librarian.md)
    - `audio`: [Audio properties.](https://github.com/threedworld-mit/tdw/blob/master/Documentation/python/py_impact.md#objectinfo)
    """

    def __init__(self, index: int, rigidbodies: Rigidbodies, segmentation_colors: SegmentationColors,
                 audio: ObjectInfo):
        """
        :param index: The index of the object in `segmentation_colors`
        :param rigidbodies: Rigidbodies output data.
        :param segmentation_colors: Segmentation colors output data.
        """

        self.object_id = segmentation_colors.get_object_id(index)
        self.model_name = segmentation_colors.get_object_name(index)
        self.segmentation_color = np.array(segmentation_colors.get_object_color(index))
        self.audio = audio

        # Get the mass.
        self.mass: float = -1
        for i in range(rigidbodies.get_num()):
            if rigidbodies.get_id(i) == self.object_id:
                self.mass = rigidbodies.get_mass(i)
                break
        assert self.mass >= 0, f"Mass not found: {self.object_id}"
