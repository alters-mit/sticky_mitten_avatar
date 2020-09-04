from sticky_mitten_avatar import StickyMittenAvatarController


class TestController(StickyMittenAvatarController):
    """
    Initialize a simple scene and an avatar in debug mode.

    The build will show IK targets and the controller will output IK solution plots.
    """

    def _init_avatar(self) -> None:
        """
        Initialize the avatar.
        """

        self.create_avatar(avatar_id="a", debug=True)
