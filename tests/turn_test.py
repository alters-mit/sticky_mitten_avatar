from typing import List
from sticky_mitten_avatar import StickyMittenAvatarController
from sticky_mitten_avatar.task_status import TaskStatus


class TurnTest(StickyMittenAvatarController):
    """
    Test the avatar turning nearly 360 degrees.
    """

    def __init__(self, port: int = 1071):
        super().__init__(port=port, launch_build=False)
        self.o_1 = 0
        self.o_2 = 1

    def _get_scene_init_commands(self, scene: str = None, layout: int = None) -> List[dict]:
        commands = super()._get_scene_init_commands()
        self.o_1, o_1_commands = self._add_object("jug05", position={"x": 0.2, "y": 0, "z": -1.5})
        commands.extend(o_1_commands)
        self.o_2, o_2_commands = self._add_object("jug05", position={"x": -0.2, "y": 0, "z": 1.5})
        commands.extend(o_2_commands)
        return commands


if __name__ == "__main__":
    c = TurnTest()
    c.init_scene()
    status = c.turn_to(target=c.o_1)
    assert status == TaskStatus.success, status
    status = c.turn_to(target=c.o_2)
    assert status == TaskStatus.success, status
    c.end()
