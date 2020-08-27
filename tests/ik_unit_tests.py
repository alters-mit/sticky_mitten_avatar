from tdw.tdw_utils import TDWUtils
from sticky_mitten_avatar.avatars import Arm
from sticky_mitten_avatar.sma_controller import StickyMittenAvatarController


class IKUnitTests(StickyMittenAvatarController):
    """
    Unit tests for the arms of the sticky mitten avatar.
    """

    def __init__(self, port: int = 1071):
        super().__init__(port=port, launch_build=False)
        # Create an empty room.
        self.start()
        self.communicate(TDWUtils.create_empty_room(12, 12))
        self.end_scene_setup()
        self.id = "a"

    def do_test(self, test) -> None:
        """
        Create an avatar. Run a test. Stop the test.

        :param test: The test as a function.
        """

        # Create the avatar.
        self.create_avatar(avatar_id=self.id, debug=True)
        # Run the test.
        test()
        # End the test.
        self.destroy_avatar(avatar_id=self.id)

    def raise_arms(self) -> None:
        """
        Test: Both arms raise symmetrically.
        """

        c.bend_arm(avatar_id=self.id, target={"x": -0.2, "y": 0.4, "z": 0.385}, arm=Arm.left)
        c.bend_arm(avatar_id=self.id, target={"x": 0.2, "y": 0.4, "z": 0.385}, arm=Arm.right)

    def ik_rotation(self) -> None:
        """
        Test: IK target follows avatar rotation.
        """

        d_theta = 15
        theta = 15
        while theta < 360:
            c.communicate({"$type": "rotate_avatar_by",
                           "angle": theta,
                           "axis": "yaw",
                           "is_world": True,
                           "avatar_id": self.id})

            c.bend_arm(avatar_id=self.id, target={"x": -0.4, "y": 0.3, "z": 0.185}, arm=Arm.left, absolute=False)
            c.bend_arm(avatar_id=self.id, target={"x": 0.4, "y": 0.3, "z": 0.185}, arm=Arm.right, absolute=False)
            c.reset_arms(avatar_id=self.id)
            theta += d_theta


if __name__ == "__main__":
    c = IKUnitTests()
    # c.do_test(c.raise_arms)
    c.do_test(c.ik_rotation)




