from typing import List
from sticky_mitten_avatar import StickyMittenAvatarController, Arm


class PutInHeldContainer(StickyMittenAvatarController):
    def __init__(self, port: int = 1071):
        # Set demo=False for an actual simulation.
        super().__init__(port=port, launch_build=False, id_pass=False, demo=True)
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

    # This will make the simulation run slower and should only be added for demoing or debugging.
    c.add_overhead_camera({"x": -0.08, "y": 1.25, "z": 1.41}, target_object="a", images="cam")

    # Grasp each object.
    c.grasp_object(object_id=c.object_id, arm=Arm.right)
    c.grasp_object(object_id=c.container_id, arm=Arm.left)

    # Put the object in the container.
    c.put_in_container(object_id=c.object_id, container_id=c.container_id, arm=Arm.right)
    c.reset_arm(arm=Arm.right)

    # Pour out the object.
    c.pour_out(arm=Arm.left)
    c.reset_arm(arm=Arm.left)
    c.end()
