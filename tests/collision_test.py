from typing import List
from tdw.tdw_utils import TDWUtils
from sticky_mitten_avatar import StickyMittenAvatarController
from sticky_mitten_avatar.task_status import TaskStatus


class CollisionTest(StickyMittenAvatarController):
    """
    Test whether the avatar stops when it collides with a large object.
    """

    def __init__(self, port: int = 1071):
        super().__init__(port=port, launch_build=False, demo=False)
        self.o_id = 0

    def _get_scene_init_commands(self, scene: str = None, layout: int = None, room: int = -1) -> List[dict]:
        commands = [{"$type": "load_scene",
                     "scene_name": "ProcGenScene"},
                    TDWUtils.create_empty_room(4, 4)]
        self.o_id, o_commands = self._add_object("trunck",
                                                 position={"x": 0, "y": 0, "z": 1})
        commands.extend(o_commands)
        return commands


if __name__ == "__main__":
    c = CollisionTest()
    c.init_scene()
    # Crash into the object and stop.
    result = c.go_to(target=c.o_id)
    assert result == TaskStatus.collided_with_something_heavy, result
    # Crash into a wall and stop.
    result = c.go_to(target={"x": 1.85, "y": 0, "z": -0.36})
    assert result == TaskStatus.collided_with_environment, result
    c.end()
