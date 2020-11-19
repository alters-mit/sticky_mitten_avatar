from json import loads
from pathlib import Path
from typing import List, Dict, Optional
from tdw.tdw_utils import TDWUtils
from tdw.py_impact import ObjectInfo, AudioMaterial
from sticky_mitten_avatar import Arm
from sticky_mitten_avatar.util import CONTAINER_MASS, CONTAINER_SCALE, TARGET_OBJECT_MASS
from sticky_mitten_avatar.demo_controller import DemoController


class PickUpDemo(DemoController):
    def run(self) -> None:
        self.init_scene(scene="2c", layout=1, room=1, target_objects_room=1)
        container_id: Optional[int] = None
        for object_id in self.static_object_info:
            if self.static_object_info[object_id].container:
                container_id = object_id
                break
        assert container_id is not None, "No container in this scene. Re-run the controller."
        self.communicate({"$type": "teleport_object",
                          "id": container_id,
                          "position": {"x": -8.43, "y": 0, "z": -0.14}})
        self._wait_for_objects_to_stop([container_id])
        container_arm = Arm.left
        object_arm = Arm.right
        self._go_to_and_lift(object_id=container_id, arm=container_arm, stopping_distance=0.4)
        for i in range(4):
            object_id = self._target_object_ids[i]
            self._go_to_and_lift(object_id, arm=object_arm, stopping_distance=0.3)
            self.put_in_container(object_id=object_id, container_id=container_id, arm=object_arm)
        