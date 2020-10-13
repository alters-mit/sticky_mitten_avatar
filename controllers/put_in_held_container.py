from typing import List
from sticky_mitten_avatar import StickyMittenAvatarController, Arm


class PutInHeldContainer(StickyMittenAvatarController):
    def __init__(self, port: int = 1071):
        super().__init__(port=port, launch_build=False, id_pass=False)
        self.container_id = 0
        self.object_id = 1

    def _get_scene_init_commands(self, scene: str = None, layout: int = None) -> List[dict]:
        commands = super()._get_scene_init_commands()
        self.container_id, container_commands = self._add_object("basket_18inx18inx12iin",
                                                                 scale={"x": 0.4, "y": 0.4, "z": 0.4},
                                                                 position={"x": -0.215, "y": 0, "z": 0.216})
        # Place a container and a jug directly in front of the avatar.
        commands.extend(container_commands)
        self.object_id, object_commands = self._add_object("jug05",
                                                           position={"x": 0.215, "y": 0, "z": 0.116},
                                                           scale={"x": 0.3, "y": 0.3, "z": 0.3})
        commands.extend(object_commands)
        return commands


if __name__ == "__main__":
    c = PutInHeldContainer()
    c.init_scene()

    # Grasp each object.
    c.grasp_object(object_id=c.object_id, arm=Arm.right)
    c.grasp_object(object_id=c.container_id, arm=Arm.left)

    # Lift up the container.
    print(c.reach_for_target(target={"x": -0.25, "y": 0.1, "z": 0.32}, arm=Arm.left, stop_on_mitten_collision=False))
    status = c.put_in_container(object_id=c.object_id, container_id=c.container_id, arm=Arm.right)
    print(status)
