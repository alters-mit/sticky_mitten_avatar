from typing import Optional
import numpy as np
from json import loads
from pathlib import Path
from pkg_resources import resource_filename
from tdw.output_data import SegmentationColors, Rigidbodies, Bounds
from tdw.py_impact import ObjectInfo
from tdw.object_init_data import TransformInitData


class StaticObjectInfo:
    """
    Info for an object that doesn't change between frames.

    Fields:

    - `object_id`: The unique ID of the object.
    - `mass`: The mass of the object.
    - `segmentation_color`: The RGB segmentation color for the object as a numpy array.
    - `model_name`: [The name of the model.](https://github.com/threedworld-mit/tdw/blob/master/Documentation/python/librarian/model_librarian.md)
    - `category`: The semantic category of the object.
    - `audio`: [Audio properties.](https://github.com/threedworld-mit/tdw/blob/master/Documentation/python/py_impact.md#objectinfo)
    - `container`': If True, this object is container-shaped (a bowl or open basket that smaller objects can be placed in).
    - `kinematic`: If True, this object is kinematic, and won't respond to physics. Example: a painting hung on a wall.
    - `size`: The size of the object as a numpy array: `[width, height, length]`
    """

    # The names of every container model.
    _CONTAINERS = ["basket_18inx18inx12iin", "basket_18inx18inx12iin_bamboo", "basket_18inx18inx12iin_plastic_lattice",
                   "basket_18inx18inx12iin_wicker", "basket_18inx18inx12iin_wood_mesh", "box_18inx18inx12in_cardboard",
                   "box_24inx18inx12in_cherry", "box_tapered_beech", "box_tapered_white_mesh",
                   "round_bowl_large_metal_perf", "round_bowl_large_padauk", "round_bowl_large_thin",
                   "round_bowl_small_beech", "round_bowl_small_walnut", "round_bowl_talll_wenge",
                   "shallow_basket_white_mesh", "shallow_basket_wicker"]
    # Objects that we can assume are kinematic.
    _KINEMATIC = ['24_in_wall_cabinet_white_wood', '24_in_wall_cabinet_wood_beach_honey',
                  '36_in_wall_cabinet_white_wood', '36_in_wall_cabinet_wood_beach_honey', 'blue_rug',
                  'cabinet_24_door_drawer_wood_beach_honey', 'cabinet_24_singledoor_wood_beach_honey',
                  'cabinet_24_two_drawer_white_wood', 'cabinet_24_two_drawer_wood_beach_honey', 'cabinet_24_white_wood',
                  'cabinet_24_wood_beach_honey', 'cabinet_36_white_wood', 'cabinet_36_wood_beach_honey',
                  'cabinet_full_height_white_wood', 'cabinet_full_height_wood_beach_honey', 'carpet_rug',
                  'elf_painting', 'flat_woven_rug', 'framed_painting', 'fruit_basket', 'its_about_time_painting',
                  'purple_woven_rug', 'silver_frame_painting']
    _COMPOSITE_OBJECTS = loads(Path(resource_filename(__name__, "composite_object_audio.json")).read_text(
        encoding="utf-8"))

    def __init__(self, object_id: int, rigidbodies: Rigidbodies, segmentation_colors: SegmentationColors,
                 bounds: Bounds, audio: ObjectInfo):
        """
        :param object_id: The unique ID of the object.
        :param rigidbodies: Rigidbodies output data.
        :param bounds: Bounds output data.
        :param segmentation_colors: Segmentation colors output data.
        """

        self.object_id = object_id
        self.audio = audio
        self.model_name = self.audio.name
        self.container = self.model_name in StaticObjectInfo._CONTAINERS
        self.kinematic = self.model_name in StaticObjectInfo._KINEMATIC

        self.category = ""
        # This is a sub-object of a composite object.
        if self.audio.library == "":
            # Get the record of the composite object.
            for k in StaticObjectInfo._COMPOSITE_OBJECTS:
                for v in StaticObjectInfo._COMPOSITE_OBJECTS[k]:
                    if v == self.audio.name:
                        record = TransformInitData.LIBRARIES["models_core.json"].get_record(k)
                        # Get the semantic category.
                        self.category = record.wcategory
                        break
        else:
            # Get the model record from the audio data.
            record = TransformInitData.LIBRARIES[self.audio.library].get_record(self.audio.name)
            # Get the semantic category.
            self.category = record.wcategory

        # Get the segmentation color.
        self.segmentation_color: Optional[np.array] = None
        for i in range(segmentation_colors.get_num()):
            if segmentation_colors.get_object_id(i) == self.object_id:
                self.segmentation_color = np.array(segmentation_colors.get_object_color(i))
                break
        assert self.segmentation_color is not None, f"Segmentation color not found: {self.object_id}"

        # Get the size of the object.
        self.size = np.array([0, 0, 0])
        for i in range(bounds.get_num()):
            if bounds.get_id(i) == self.object_id:
                self.size = np.array([float(np.abs(bounds.get_right(i)[0] - bounds.get_left(i)[0])),
                                      float(np.abs(bounds.get_top(i)[1] - bounds.get_bottom(i)[1])),
                                      float(np.abs(bounds.get_front(i)[2] - bounds.get_back(i)[2]))])
                break
        assert np.linalg.norm(self.size) > 0, f"Bounds data not found for: {self.object_id}"

        # Get the mass.
        self.mass: float = -1
        for i in range(rigidbodies.get_num()):
            if rigidbodies.get_id(i) == self.object_id:
                self.mass = rigidbodies.get_mass(i)
                break
        assert self.mass >= 0, f"Mass not found: {self.object_id}"
