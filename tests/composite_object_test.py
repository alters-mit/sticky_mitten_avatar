from typing import List
from sticky_mitten_avatar import StickyMittenAvatarController, Arm
from sticky_mitten_avatar.task_status import TaskStatus

"""
Test whether the avatar can pick up a sub-object of a composite object.
"""


class CompositeObjectTest(StickyMittenAvatarController):
    def _get_scene_init_commands(self) -> List[dict]:
        commands = super()._get_scene_init_commands()
        commands.extend(self._add_object("puzzle_box_composite", object_id=0,
                                         position={"x": 0.072, "y": 0, "z": 0.438}))
        return commands


if __name__ == "__main__":
    c = CompositeObjectTest()
    c.init_scene()
    for q in c.static_object_info:
        if c.static_object_info[q].model_name == "b03_triangle001":
            result = c.grasp_object(object_id=q, arm=Arm.right)
            assert result == TaskStatus.success, result
            break
    c.end()
