from tdw.tdw_utils import TDWUtils
from sticky_mitten_avatar.demo_controller import DemoController


class CollisionDemo(DemoController):
    """
    A demo of the avatar bumping into objects before finally picking up a container.
    This is meant to be used to generate a demo video, NOT for an actual use-case.
    """

    def __init__(self, port: int = 1071, launch_build: bool = True):
        super().__init__(port=port, launch_build=launch_build,
                         output_directory="D:/sticky_mitten_avatar_demo/collisions")

    def collisions(self) -> None:
        self.init_scene(scene="2a", layout=1, room=4, target_objects_room=4)
        container_id = self._get_container_id()
        self.communicate({"$type": "teleport_object",
                          "id": container_id,
                          "position": {"x": 6.03, "y": 0, "z": -1.49}})

        # Send the avatar to bad destinations before finally picking up the container.
        for position in [[8.26, 0, -5.32], [9.12, 0, -3.1], [5.67, 0, -0.46]]:
            self.go_to(target=TDWUtils.array_to_vector3(position))
            # Back up a bit.
            self.move_forward_by(distance=-0.5)
        # Go to the container and pick it up.
        self._go_to_and_lift(object_id=container_id, stopping_distance=0.3)
        self.move_forward_by(1)
        self.end()


if __name__ == "__main__":
    c = CollisionDemo()
    c.collisions()
