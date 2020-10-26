import numpy as np
from argparse import ArgumentParser
from tdw.tdw_utils import TDWUtils
from tdw.output_data import Images
from sticky_mitten_avatar import StickyMittenAvatarController
from sticky_mitten_avatar.util import get_data

"""
Show the occupancy map of a given scene and layout.
Show an image of the map.

Usage:

```
python3 occupancy_viwer.py --scene [SCENE] --layout [LAYOUT]
```
"""

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--scene", type=str, default="1a")
    parser.add_argument("--layout", type=int, default=0)
    args = parser.parse_args()

    c = StickyMittenAvatarController(launch_build=False, screen_width=1280, screen_height=720)
    c.init_scene(scene=args.scene, layout=args.layout)
    commands = [{"$type": "set_floorplan_roof",
                 "show": False}]
    # Add position markers at each occupancy position.
    for ix, iy in np.ndindex(c.occupancy_map.shape):
        if c.occupancy_map[ix][iy] == 1:
            x, z = c.get_occupancy_position(ix, iy)
            commands.append({"$type": "add_position_marker",
                             "position": {"x": x, "y": 0, "z": z},
                             "scale": 0.3})
    commands.extend(TDWUtils.create_avatar(avatar_id="c",
                                           position={"x": 0, "y": 31, "z": 0},
                                           look_at=TDWUtils.VECTOR3_ZERO))
    commands.extend([{"$type": "toggle_image_sensor",
                      "sensor_name": "SensorContainer"},
                     {"$type": "set_pass_masks",
                      "pass_masks": ["_img"],
                      "avatar_id": "c"},
                     {"$type": "send_images",
                      "ids": ["c"]}])
    resp = c.communicate(commands)
    print(resp)
    images = get_data(resp=resp, d_type=Images)
    pil_image = TDWUtils.get_pil_image(images, 0)
    pil_image.show()
