from typing import List
from sticky_mitten_avatar import StickyMittenAvatarController, Arm
from sticky_mitten_avatar.task_status import TaskStatus
from sticky_mitten_avatar.util import CONTAINER_MASS, TARGET_OBJECT_MASS, CONTAINER_SCALE


class FillAndPour(StickyMittenAvatarController):
    """
    Fill a container with objects.
    This controller includes a very basic system for aligning the avatar with an object such it can be picked up.

    1. Create a scene with an avatar, a container, and several objects.
    2. Go to each object and put the object in the container.
    """

    def __init__(self, port: int = 1071):
        # `demo=True` only because this is a demo controller.
        # In an actual simulation, set it to `False`.
        super().__init__(port=port, launch_build=False, id_pass=False, demo=True)
        self.container_id = 0
        self.jug_ids = []

    def _get_scene_init_commands(self, scene: str = None, layout: int = None, room: int = -1) -> List[dict]:
        # Don't include this function in an actual simulation.
        # Use `init_scene()` with `scene` and `layout` parameters instead.
        commands = super()._get_scene_init_commands()
        self.container_id, container_commands = self._add_object("basket_18inx18inx12iin",
                                                                 scale=CONTAINER_SCALE,
                                                                 position={"x": -0.215, "y": 0, "z": 0.341})
        commands.extend(container_commands)

        # Low-level command to adjust the mass of the object to something reasonable.
        # You won't need to do this in an actual simulation.
        # If the `scene` and `layout` parameters are set, the mass is handled automatically.
        commands.append({"$type": "set_mass",
                         "id": self.container_id,
                         "mass": CONTAINER_MASS})
        x = 0.215
        z = 0.516
        for i in range(2):
            o_id, object_commands = self._add_object("jug05",
                                                     position={"x": x, "y": 0, "z": z + i * 0.5},
                                                     scale={"x": 0.5, "y": 0.5, "z": 0.5})
            commands.extend(object_commands)

            # See comments above regarding mass.
            commands.append({"$type": "set_mass",
                             "id": o_id,
                             "mass": TARGET_OBJECT_MASS})
            self.jug_ids.append(o_id)
        return commands

    def init_scene(self, scene: str = None, layout: int = None, room: int = -1) -> None:
        super().init_scene(scene=scene, layout=layout, room=room)
        for o_id in self.jug_ids:
            self.static_object_info[o_id].target_object = True


if __name__ == "__main__":
    c = FillAndPour()
    c.init_scene()
    # This will make the simulation run slower and should only be added for demoing or debugging.
    c.add_overhead_camera({"x": -0.99, "y": 1.25, "z": 1.41}, target_object="a", images="cam")

    # This is a very basic algorithm for aligning the avatar with an object:
    #
    # 1. Try to grasp the object.
    # 2. If the avatar's arm can't reach for the object, turn the avatar and try again.
    #
    # This might be too simple for your controller! You can try the following:
    #
    # - Adjust `d_theta` depending on which mitten is initially closer to the object.
    # - Try moving forwards or backing away.
    # - Try checking if there is an obstacle in the way. If so, move it out of the way and try again.
    # - Something else!
    lift_container_target = {"x": -0.2, "y": 0.4, "z": 0.32}
    d_theta = -15
    for object_id in c.static_object_info:
        # Don't try to pick up a container.
        if c.static_object_info[object_id].container:
            continue

        # Grasp the container (ignored if the container is already being grasped).
        status = c.grasp_object(object_id=c.container_id, arm=Arm.left, stop_on_mitten_collision=False)
        assert status == TaskStatus.success, status
        # Lift the container.
        c.reach_for_target(target=lift_container_target,
                           arm=Arm.left,
                           check_if_possible=False,
                           stop_on_mitten_collision=False)

        # Go to the target object.
        c.go_to(target=object_id)
        # Turn until you can grasp the object.
        theta = 0
        grasped = False

        # Try turning 45 degrees before giving up.
        # You can try adjusting this maximum.
        while theta < 45 and not grasped:
            # Try to grasp the object.
            status = c.grasp_object(object_id=object_id, arm=Arm.right)
            if status == TaskStatus.success:
                grasped = True
                break
            # Turn a bit and try again.
            if not grasped:
                c.turn_by(d_theta)
                theta += d_theta
        assert grasped, "Failed to pick up object."

        # Put the object in the container.
        status = c.put_in_container(object_id=object_id, container_id=c.container_id, arm=Arm.right)
        assert status == TaskStatus.success, status
        c.reset_arm(arm=Arm.left)
    # Move forward a little more.
    c.reach_for_target(target=lift_container_target,
                       arm=Arm.left,
                       check_if_possible=False,
                       stop_on_mitten_collision=False)
    c.move_forward_by(0.8)
    # End the simulation.
    c.end()
