from pathlib import Path
import numpy as np
from typing import Union, List, Optional, Tuple
from tdw.tdw_utils import TDWUtils
from tdw.output_data import OutputData, Images
from sticky_mitten_avatar import StickyMittenAvatarController, Arm
from sticky_mitten_avatar.task_status import TaskStatus


class NavigationDemo(StickyMittenAvatarController):
    def _get_scene_init_commands(self, scene: str = None, layout: int = None, room: int = -1,
                                 target_objects_room: int = -1) -> List[dict]:
        # Initialize the floorplan.
        commands = self.get_scene_init_commands(scene="5b", layout=2, audio=True)


