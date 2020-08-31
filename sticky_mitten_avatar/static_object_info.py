import numpy as np
from tdw.output_data import SegmentationColors, Bounds, Volumes, Rigidbodies
from tdw.py_impact import ObjectInfo


class StaticObjectInfo:
    """
    Info for an object that doesn't change between frames.

    Fields:

    - `object_id`: The unique ID of the object.
    - `mass`: The mass of the object.
    - `segmentation_color`: The RGB segmentation color.
    - `model_name`: The name of the object's [model](https://github.com/threedworld-mit/tdw/blob/master/Documentation/python/librarian/model_librarian.md)
    - `volume`: The "naive" volume: length * width * height, assuming the object was brick-shaped.
    - `hollowness`: The percentage (between 0 and 1) of the object's volume that is empty space.
    - `audio`: Audio properties.
    """

    def __init__(self, index: int, rigidbodies: Rigidbodies, segmentation_colors: SegmentationColors,
                 bounds: Bounds, volumes: Volumes, audio: ObjectInfo):
        """
        :param index: The index of the object in `segmentation_colors`
        :param rigidbodies: Rigidbodies output data.
        :param segmentation_colors: Segmentation colors output data.
        :param bounds: Bounds output data.
        :param volumes: Volumes output data.
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

        # Get the "box volume" from the bounds data.
        self.volume = -1
        for i in range(bounds.get_num()):
            if bounds.get_id(i) == self.object_id:
                self.volume = np.linalg.norm(np.array(bounds.get_left(i)) - np.array(bounds.get_right(i))) * \
                              np.linalg.norm(np.array(bounds.get_top(i)) - np.array(bounds.get_bottom(i))) * \
                              np.linalg.norm(np.array(bounds.get_front(i)) - np.array(bounds.get_back(i)))
                break
        assert self.volume >= 0, f"Bounds data not found for: {self.object_id}"

        v = -1
        for i in range(volumes.get_num()):
            if volumes.get_object_id(i) == self.object_id:
                v = volumes.get_volume(i)
                break
        assert v >= 0, f"Volumes data not found for: {self.object_id}"

        # Calculate the "hollowness" from the volume.
        self.hollowness = 1 - (v / self.volume)
