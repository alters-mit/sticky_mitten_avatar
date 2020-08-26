from tdw.tdw_utils import TDWUtils
from sticky_mitten_avatar.avatars import Arm
from sticky_mitten_avatar.sma_controller import StickyMittenAvatarController

"""
Test the IK chain of each arm.
"""

if __name__ == "__main__":
    c = StickyMittenAvatarController(launch_build=False)
    c.start()

    commands = [TDWUtils.create_empty_room(12, 12)]
    c.communicate(commands)

    avatar_id = "a"
    c.create_avatar(avatar_id=avatar_id, debug=True)
    c.end_scene_setup()
    c.bend_arm(avatar_id=avatar_id, target={"x": -0.2, "y": 0.4, "z": 0.385}, arm=Arm.left)
    c.bend_arm(avatar_id=avatar_id, target={"x": 0.2, "y": 0.4, "z": 0.385}, arm=Arm.right)
