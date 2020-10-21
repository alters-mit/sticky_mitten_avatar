from pathlib import Path
from typing import List
from tdw.output_data import Images
from tdw.tdw_utils import TDWUtils
from sticky_mitten_avatar import StickyMittenAvatarController, Arm
from sticky_mitten_avatar.util import get_data


class SocialImage(StickyMittenAvatarController):
    """
    Generate the image used for the GitHub social preview card.
    """

    def __init__(self):
        super().__init__(launch_build=True, id_pass=False, demo=True, screen_width=1024, screen_height=1024)
        self.container_id = 0

    def _get_scene_init_commands(self, scene: str = None, layout: int = None) -> List[dict]:
        commands = super()._get_scene_init_commands(scene=scene, layout=layout)
        # Add a container to the scene.
        self.container_id, container_commands = self._add_object("basket_18inx18inx12iin_plastic_lattice",
                                                                 scale={"x": 0.4, "y": 0.4, "z": 0.4},
                                                                 position={"x": -8.788, "y": 0, "z": 0.556})
        commands.extend(container_commands)
        commands.append({"$type": "set_mass",
                         "id": self.container_id,
                         "mass": 1})
        return commands


if __name__ == "__main__":
    c = SocialImage()
    c.init_scene(scene="2a", layout=1, room=1)

    # Add a third-person camera.
    c.add_overhead_camera({"x": -9.39, "y": 0.65, "z": 2.18}, target_object="a", images="cam")

    # Grasp and pick up the container.
    c.grasp_object(object_id=c.container_id, arm=Arm.right)
    c.reach_for_target(target={"x": 0.2, "y": 0.2, "z": 0.3}, arm=Arm.right)

    # Use low-level commands to rotate the head and save an image.
    # Don't use these in an actual simulation!
    # To rotate the camera, see: `StickyMittenAvatar.rotate_camera_by()`
    # To save an image, see: `FrameData`
    resp = c.communicate([{"$type": "rotate_head_by",
                           "axis": "pitch",
                           "angle": 40},
                          {"$type": "rotate_head_by",
                           "axis": "yaw",
                           "angle": 15},
                          {"$type": "send_images",
                           "frequency": "once",
                           "avatar_id": "c"}])
    # Save the image.
    TDWUtils.save_images(images=get_data(resp=resp, d_type=Images),
                         output_directory=str(Path("..").resolve()),
                         filename="social",
                         append_pass=False)
    c.end()
