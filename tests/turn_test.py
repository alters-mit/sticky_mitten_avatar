from typing import List
from sticky_mitten_avatar import StickyMittenAvatarController
from sticky_mitten_avatar.task_status import TaskStatus


class TurnTest(StickyMittenAvatarController):
    """
    Test the avatar turning nearly 360 degrees.
    """

    def __init__(self, port: int = 1071, launch_build: bool = True, ):
        super().__init__(port=port, launch_build=launch_build)
        self.object_id = self.get_unique_id()

    def _get_scene_init_commands(self, scene: str = None, layout: int = None) -> List[dict]:
        commands = super()._get_scene_init_commands()
        self.object_id, jug_commands = self._add_object("jug05", position={"x": 0.2, "y": 0, "z": -1.5})
        commands.extend(jug_commands)
        return commands


if __name__ == "__main__":
    c = TurnTest(launch_build=False)
    c.init_scene()
    status = c.turn_to(target=c.object_id)
    assert status == TaskStatus.success, status
