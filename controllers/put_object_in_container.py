from pathlib import Path
from typing import List, Union
from tdw.tdw_utils import TDWUtils
from tdw.output_data import Images
from sticky_mitten_avatar.avatars import Arm
from sticky_mitten_avatar import StickyMittenAvatarController
from sticky_mitten_avatar.util import get_data


class PutObjectInContainer(StickyMittenAvatarController):
    """
    1. Create a sticky mitten avatar, a jug, and a container. Add an overhead camera for image capture.
    2. The avatar picks up the jug.
    3. The avatar goes to the container.
    4. The avatar puts the jug in the container.

    Save an image per frame.
    """

    def __init__(self, output_dir: str, port: int = 1071, launch_build: bool = True):
        """
        :param output_dir: The output directory for images.
        :param port: The port number.
        :param launch_build: If True, automatically launch the build.
        """

        self.output_dir = Path(output_dir)
        if not self.output_dir.exists():
            self.output_dir.mkdir(parents=True)
        self.output_dir = str(self.output_dir.resolve())
        print(f"Images will be saved to: {self.output_dir}")

        super().__init__(port=port, launch_build=launch_build)

        # Save images every frame, if possible.
        self.frame_count = 0
        self.o_id = self.get_unique_id()
        self.bowl_id = self.get_unique_id()

    def communicate(self, commands: Union[dict, List[dict]]) -> List[bytes]:
        resp = super().communicate(commands)

        # Save images per frame.
        images = get_data(resp=resp, d_type=Images)
        if images is not None:
            TDWUtils.save_images(images=images,
                                 filename=TDWUtils.zero_padding(self.frame_count, width=4),
                                 output_directory=self.output_dir)
            self.frame_count += 1
        return resp

    def _get_scene_init_commands(self) -> List[dict]:
        commands = super()._get_scene_init_commands()
        # Add a jug.
        commands.extend(self._add_object("jug05",
                                         position={"x": -0.2, "y": 0, "z": 0.285},
                                         object_id=self.o_id,
                                         scale={"x": 0.8, "y": 0.8, "z": 0.8}))
        # Add a container.
        bowl_position = {"x": 1.2, "y": 0, "z": 0.25}
        commands.extend(self._add_object("serving_bowl",
                                         position=bowl_position,
                                         rotation={"x": 0, "y": 30, "z": 0},
                                         object_id=self.bowl_id,
                                         scale={"x": 1.3, "y": 1, "z": 1.3}))
        return commands

    def _do_scene_init_late(self) -> None:
        # Add a third-person camera.
        self.add_overhead_camera({"x": -0.08, "y": 1.25, "z": 1.41}, target_object="a", images="cam")

    def run(self) -> None:
        """
        Run a single trial. Save images per frame.
        """

        self.init_scene()

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
        for i in range(50):
            self.communicate([])
        # Stop the build.
        self.end()


if __name__ == "__main__":
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("--dir", default="images", type=str, help="Output directory for images.")
    args = parser.parse_args()

    PutObjectInContainer(output_dir=args.dir).run()
