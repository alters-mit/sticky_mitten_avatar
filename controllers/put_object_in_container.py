from typing import List
from sticky_mitten_avatar.avatars import Arm
from sticky_mitten_avatar import StickyMittenAvatarController


class PutObjectInContainer(StickyMittenAvatarController):
    """
    1. Create a sticky mitten avatar, a jug, and a container. Add an overhead camera for image capture.
    2. The avatar picks up the jug.
    3. The avatar goes to the container.
    4. The avatar puts the jug in the container.

    Save an image per frame.
    """

    def __init__(self, port: int = 1071, launch_build: bool = True):
        """
        :param port: The port number.
        :param launch_build: If True, automatically launch the build.
        """

        super().__init__(port=port, launch_build=launch_build, audio=False, id_pass=False, demo=True)

        # Save images every frame, if possible.
        self.o_id = 0
        self.bowl_id = 1

    def _get_scene_init_commands(self, scene: str = None, layout: int = None) -> List[dict]:
        commands = super()._get_scene_init_commands()
        # Add a jug.
        self.o_id, jug_commands = self._add_object("jug05",
                                                   position={"x": -0.2, "y": 0, "z": 0.285},
                                                   scale={"x": 0.8, "y": 0.8, "z": 0.8})
        commands.extend(jug_commands)
        # Add a container.
        bowl_position = {"x": 1.2, "y": 0, "z": 0.25}
        self.bowl_id, bowl_commands = self._add_object("serving_bowl",
                                                       position=bowl_position,
                                                       rotation={"x": 0, "y": 30, "z": 0},
                                                       scale={"x": 1.3, "y": 1, "z": 1.3})
        commands.extend(bowl_commands)
        return commands

    def run(self) -> None:
        """
        Run a single trial. Save images per frame.
        """

        self.init_scene()

        # Add a third-person camera.
        self.add_overhead_camera({"x": -0.08, "y": 1.25, "z": 1.41}, target_object="a", images="cam")

        # Pick up the object.
        self.grasp_object(object_id=self.o_id, arm=Arm.left)

        # Lift the object up a bit.
        self.reach_for_target(target={"x": -0.1, "y": 0.6, "z": 0.32}, arm=Arm.left)

        # Go to the bowl.
        self.go_to(target=self.bowl_id, move_stopping_threshold=0.3)

        self.turn_to(target=self.bowl_id)

        # Lift the object up a bit.
        self.reach_for_target(target={"x": -0.1, "y": 0.6, "z": 0.5}, arm=Arm.left)
        # Drop the object in the container.
        self.drop()
        # Stop the build.
        self.end()


if __name__ == "__main__":
    PutObjectInContainer().run()
