from typing import List, Dict
from tdw.tdw_utils import TDWUtils
from sticky_mitten_avatar.sma_controller import StickyMittenAvatarController
from sticky_mitten_avatar.scene_recipes import SceneRecipe


class Simple(SceneRecipe):
    """
    An empty minimal room.
    """

    def _get_scene_commands(self, c: StickyMittenAvatarController) -> List[dict]:
        return[{"$type": "load_scene",
                "scene_name": "ProcGenScene"},
               TDWUtils.create_empty_room(12, 12)]

    def _get_avatar_position(self) -> Dict[str, float]:
        return TDWUtils.VECTOR3_ZERO

    def _get_avatar_rotation(self) -> float:
        return 0
