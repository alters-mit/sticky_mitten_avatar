from tdw.tdw_utils import TDWUtils
from sticky_mitten_avatar.avatars import Arm
from sticky_mitten_avatar.sma_controller import StickyMittenAvatarController

"""
Test IK targets as the avatar rotates.
"""

if __name__ == "__main__":
    c = StickyMittenAvatarController(launch_build=False)
    c.start()
    c.communicate(TDWUtils.create_empty_room(12, 12))

    avatar_id = "a"
    c.create_avatar(avatar_id=avatar_id, debug=True)
    c.end_scene_setup()
    d_theta = 15
    theta = 30
    while theta < 360:
        c.communicate({"$type": "rotate_avatar_by",
                       "angle": theta,
                       "axis": "yaw",
                       "is_world": True,
                       "avatar_id": avatar_id})
        c.bend_arm(avatar_id=avatar_id, target={"x": -0.2, "y": 0.4, "z": 0.385}, arm=Arm.left, absolute=False)
        c.bend_arm(avatar_id=avatar_id, target={"x": 0.2, "y": 0.4, "z": 0.385}, arm=Arm.right, absolute=False)
        c.reset_arms(avatar_id=avatar_id)
        theta += d_theta

