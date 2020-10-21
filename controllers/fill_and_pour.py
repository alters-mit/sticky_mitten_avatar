from typing import List
from sticky_mitten_avatar import StickyMittenAvatarController, Arm
from sticky_mitten_avatar.task_status import TaskStatus
from sticky_mitten_avatar.util import CONTAINER_MASS, TARGET_OBJECT_MASS, CONTAINER_SCALE


class FillAndPour(StickyMittenAvatarController):
    """
    Fill a container with objects and pour objects out when the container is full.
    This controller includes a very basic system for aligning the avatar with an object such it can be picked up.

    1. Create a scene with an avatar, a container, and several objects.
    2. Go to each object and put the object in the container.
    3. If the container is full, pour out the contents and then try again to put the object in the container.
    """

    def __init__(self, port: int = 1071):
        # `demo=True` only because this is a demo controller.
        # In an actual simulation, set it to `False`.
        super().__init__(port=port, launch_build=False, id_pass=False, demo=True)
        self.container_id = 0

    def _get_scene_init_commands(self, scene: str = None, layout: int = None) -> List[dict]:
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
        z = 0.116
        for i in range(3):
            o_id, object_commands = self._add_object("jug05",
                                                     position={"x": x, "y": 0, "z": z + i * 0.5},
                                                     scale={"x": 0.5, "y": 0.5, "z": 0.5})
            commands.extend(object_commands)

            # See comments above regarding mass.
            commands.append({"$type": "set_mass",
                             "id": o_id,
                             "mass": TARGET_OBJECT_MASS})
        return commands


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
    d_theta = -15
    for object_id in c.static_object_info:
        # Don't try to pick up a container.
        if c.static_object_info[object_id].container:
            continue

        # Grasp the container (ignored if the container is already being grasped).
        status = c.grasp_object(object_id=c.container_id, arm=Arm.left, stop_on_mitten_collision=False)
        assert status == TaskStatus.success, status
        # Lift the container.
        c.reach_for_target(target={"x": -0.2, "y": 0.2, "z": 0.32},
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
        # This container is full. Pour some stuff out.
        if status == TaskStatus.full_container:
            c.pour_out_container(arm=Arm.left)
            status = c.put_in_container(object_id=object_id, container_id=c.container_id, arm=Arm.right)
        # If the container isn't full, verify that the object is in the container.
        else:
            if status != TaskStatus.success:
                while True:
                    c.communicate([])
            assert status == TaskStatus.success, status

        # Move the arms away.
        c.reach_for_target(target={"x": -0.2, "y": 0.15, "z": 0.32}, arm=Arm.left)
        c.reset_arm(arm=Arm.right)
    # End the simulation.
    c.end()
