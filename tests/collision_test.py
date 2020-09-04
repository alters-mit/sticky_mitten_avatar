from typing import List
from tdw.tdw_utils import TDWUtils
from sticky_mitten_avatar.test_controller import TestController

"""
Test whether the avatar stops when it collides with a large object.
"""


class CollisionTest(TestController):
    def _get_scene_init_commands_early(self) -> List[dict]:
        commands = [{"$type": "load_scene",
                     "scene_name": "ProcGenScene"},
                    TDWUtils.create_empty_room(4, 4)]
        commands.extend(self.get_add_object("trunck",
                                            position={"x": 0, "y": 0, "z": 1},
                                            rotation={"x": 0, "y": 0, "z": 0},
                                            object_id=o_id))
        return commands


if __name__ == "__main__":
    o_id = 0
    c = CollisionTest(launch_build=False)
    c.init_scene()
    # Crash into the object and stop.
    success = c.go_to(avatar_id="a", target=o_id)
    assert not success
    # Crash into a wall and stop.
    success = c.go_to(avatar_id="a", target={"x": 1.85, "y": 0, "z": -0.36})
    assert not success
