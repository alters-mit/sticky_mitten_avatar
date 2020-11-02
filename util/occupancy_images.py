from json import loads
from pathlib import Path
import numpy as np
from tdw.tdw_utils import TDWUtils
from tdw.output_data import Images
from tdw.floorplan_controller import FloorplanController
from sticky_mitten_avatar.util import get_data, OCCUPANCY_CELL_SIZE
from sticky_mitten_avatar.paths import OCCUPANCY_MAP_DIRECTORY, SCENE_BOUNDS_PATH, OBJECT_SPAWN_MAP_DIRECTORY

"""
Create an image of each occupancy map per scene per layout.
"""

if __name__ == "__main__":
    # Use a FloorplanController instead of a StickyMittenAvatarController because
    # we don't want proc-gen objects or avatars to affect the occupancy map or the image.
    c = FloorplanController()
    # Set the screen size.
    c.communicate({"$type": "set_screen_size",
                   "width": 1280,
                   "height": 720})
    output_dir = str(Path("../images/occupancy_maps").resolve())
    print(f"Images will be saved to: {output_dir}")
    for scene in ["1", "2", "4", "5"]:
        for layout in [0, 1, 2]:
            # Load the occupancy map, the spawn map, and scene bounds.
            # This isn't handled in the controller because it isn't a StickyMittenAvatarController.
            occupancy_map = np.load(str(OCCUPANCY_MAP_DIRECTORY.joinpath(f"{scene[0]}_{layout}.npy").resolve()))
            spawn_map = np.load(str(OBJECT_SPAWN_MAP_DIRECTORY.joinpath(f"{scene[0]}_{layout}.npy").resolve()))
            scene_bounds = loads(SCENE_BOUNDS_PATH.read_text())[scene[0]]

            # Load the scene and the furniture.
            commands = c.get_scene_init_commands(scene=f"{scene}a", layout=layout, audio=True)
            # Hide the roof. Remove the position markers that were created in the previous scene.
            commands.extend([{"$type": "set_floorplan_roof",
                              "show": False},
                             {"$type": "remove_position_markers"}])
            # Add position markers at each occupancy position.
            for ix, iy in np.ndindex(occupancy_map.shape):
                if occupancy_map[ix][iy] == 1:
                    x = scene_bounds["x_min"] + (ix * OCCUPANCY_CELL_SIZE)
                    z = scene_bounds["z_min"] + (iy * OCCUPANCY_CELL_SIZE)
                    # Set a different color for a position where an object can be spawned.
                    if spawn_map[ix][iy]:
                        color = {"r": 0, "g": 0, "b": 1, "a": 1}
                    else:
                        color = {"r": 1, "g": 0, "b": 0, "a": 1}
                    commands.append({"$type": "add_position_marker",
                                     "position": {"x": x, "y": 0, "z": z},
                                     "scale": 0.3,
                                     "color": color})
            # Create an overhead camera and capture an image.
            commands.extend(TDWUtils.create_avatar(position={"x": 0, "y": 31, "z": 0},
                                                   look_at=TDWUtils.VECTOR3_ZERO))
            commands.extend([{"$type": "set_pass_masks",
                              "pass_masks": ["_img"]},
                             {"$type": "send_images"}])
            resp = c.communicate(commands)
            # Save the image.
            images = get_data(resp=resp, d_type=Images)
            TDWUtils.save_images(images=images,
                                 filename=f"{scene}_{layout}",
                                 output_directory=output_dir,
                                 append_pass=False)
            print(scene, layout)
    c.communicate({"$type": "terminate"})
