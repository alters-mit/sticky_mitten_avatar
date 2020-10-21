from sticky_mitten_avatar import StickyMittenAvatarController

"""
This is a simple example of how to initialize an interior environment populated by furniture, objects, and an avatar.
"""

if __name__ == "__main__":
    # Instantiate the controller.
    c = StickyMittenAvatarController(launch_build=False)
    # Initialize the scene. Populate it with objects. Spawn the avatar in a room.
    c.init_scene(scene="2a", layout=1, room=1)
