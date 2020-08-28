from typing import List, Dict
from tdw.tdw_utils import TDWUtils
from sticky_mitten_avatar.sma_controller import StickyMittenAvatarController
from sticky_mitten_avatar.scene_recipes import SceneRecipe


class Demo(SceneRecipe):
    def _get_scene_commands(self, c: StickyMittenAvatarController) -> List[dict]:
        commands = []
        commands.extend(c.get_add_object("woven_box",
                                         position={"x": 3.37, "y": 0, "z": -2.56},
                                         rotation={"x": 0.0, "y": 0.0, "z": 0.0},
                                         scale={"x": 1, "y": 1, "z": 1},
                                         object_id=12744007))
        commands.extend(c.get_add_object("trapezoidal_table",
                                         position={"x": 0.491, "y": 0, "z": 0},
                                         rotation={"x": 180.0, "y": 90.0, "z": 180.0},
                                         scale={"x": 1, "y": 1, "z": 1},
                                         object_id=6746554))
        commands.extend(c.get_add_object("rh10",
                                         position={"x": 0.02, "y": 0, "z": 1.582},
                                         rotation={"x": 0.0, "y": 26.000006681692533, "z": 0.0},
                                         scale={"x": 0.1, "y": 0.1, "z": 0.1},
                                         object_id=5364976))
        commands.extend(c.get_add_object("satiro_sculpture",
                                         position={"x": 1.168, "y": 0, "z": 4.402},
                                         rotation={"x": -180.0, "y": 8.899978555107223, "z": -180.0},
                                         scale={"x": 1, "y": 1, "z": 1},
                                         object_id=8709867))
        commands.extend(c.get_add_object("vitra_meda_chair",
                                         position={"x": 3.47, "y": 0, "z": -4.44},
                                         rotation={"x": 0.0, "y": 0.0, "z": 0.0},
                                         scale={"x": 1, "y": 1, "z": 1},
                                         object_id=9570582))
        commands.extend(c.get_add_object("trunck",
                                         position={"x": 3.457, "y": 0, "z": 3.984},
                                         rotation={"x": 180.0, "y": 90.0, "z": 180.0},
                                         scale={"x": 1, "y": 1, "z": 1},
                                         object_id=5291010))
        commands.extend(c.get_add_object("live_edge_coffee_table",
                                         position={"x": 2.195, "y": 0, "z": 1.525},
                                         rotation={"x": 0.0, "y": 0.0, "z": 0.0},
                                         scale={"x": 1, "y": 1, "z": 1.35},
                                         object_id=2162713))
        commands.extend(c.get_add_object("sayonara_sofa",
                                         position={"x": 2.588, "y": 0, "z": 2.513},
                                         rotation={"x": 180.0, "y": 0.0, "z": 180.0},
                                         scale={"x": 1, "y": 1, "z": 1},
                                         object_id=2544507))
        commands.extend(c.get_add_object("small_table_green_marble",
                                         position={"x": -0.248, "y": 0, "z": -4.334},
                                         rotation={"x": 0.0, "y": 0.0, "z": 0.0},
                                         scale={"x": 1, "y": 1, "z": 1},
                                         object_id=5258547))
        commands.extend(c.get_add_object("arflex_hollywood_sofa",
                                         position={"x": 0.567, "y": 0, "z": -2.153},
                                         rotation={"x": 0.0, "y": 0.0, "z": 0.0},
                                         scale={"x": 1, "y": 1, "z": 1},
                                         object_id=5922932))
        commands.extend(c.get_add_object("macbook_air",
                                         position={"x": 2.024, "y": 0.46, "z": -2.399},
                                         rotation={"x": 0.0, "y": 0.0, "z": 0.0},
                                         scale={"x": 1, "y": 1, "z": 1},
                                         object_id=1453018))
        commands.extend(c.get_add_object("alma_floor_lamp",
                                         position={"x": 3.637, "y": 0, "z": 2.45},
                                         rotation={"x": 0.0, "y": 0.0, "z": 0.0},
                                         scale={"x": 1, "y": 1, "z": 1},
                                         object_id=9067846))
        commands.extend(c.get_add_object("rope_table_lamp",
                                         position={"x": 3.4, "y": 1.0, "z": 3.946},
                                         rotation={"x": 0.0, "y": 0.0, "z": 0.0},
                                         scale={"x": 1, "y": 1, "z": 1},
                                         object_id=4919928))
        commands.extend(c.get_add_object("duffle_bag",
                                         position={"x": 2.213, "y": 0, "z": -1.578},
                                         rotation={"x": 0.0, "y": 29.550001010645264, "z": 0.0},
                                         scale={"x": 1, "y": 1, "z": 1},
                                         object_id=7313859))
        return commands
