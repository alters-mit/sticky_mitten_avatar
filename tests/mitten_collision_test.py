from typing import List
from sticky_mitten_avatar import Arm
from sticky_mitten_avatar.test_controller import TestController
from sticky_mitten_avatar.task_status import TaskStatus


class MittenCollisionTest(TestController):
    """
    Test whether a collision between a mitten and an object stops arm-bending motion.
    """

    def __init__(self, port: int = 1071):
        self.o_id = 0
        super().__init__(port=port, launch_build=False, id_pass=False)

    def _get_scene_init_commands(self, scene: str = None, layout: int = None, room:int = -1) -> List[dict]:
        # Place an object on a table.
        commands = super()._get_scene_init_commands()
        commands.extend(self._add_object(model_name="trunck", position={"x": 0, "y": 0, "z": 0.66},
                                         scale={"x": 1, "y": 0.4, "z": 1})[1])
        self.o_id, o_commands = self._add_object(model_name="jug05", position={"x": 0, "y": 0.4, "z": 0.44})
        commands.extend(o_commands)
        return commands


if __name__ == "__main__":
    c = MittenCollisionTest()
    c.init_scene()
    # Try to grasp the object. This should result in a collision.
    result = c.grasp_object(object_id=c.o_id, arm=Arm.left)
    assert result == TaskStatus.mitten_collision, result
    c.reset_arm(arm=Arm.left)
    # Try again. This should result in a failure to pick up the object.
    result = c.grasp_object(object_id=c.o_id, arm=Arm.left, stop_on_mitten_collision=False)
    assert result == TaskStatus.no_longer_bending or result == TaskStatus.failed_to_pick_up, result
    c.end()
