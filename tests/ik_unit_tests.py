from sticky_mitten_avatar.avatars import Arm
from sticky_mitten_avatar import StickyMittenAvatarController


class IKUnitTests(StickyMittenAvatarController):
    """
    Unit tests for the arms of the sticky mitten avatar.
    """

    def __init__(self, port: int = 1071):
        super().__init__(port=port, launch_build=False)
        self.id = "a"

    def do_test(self, test) -> None:
        """
        Create an avatar. Run a test. Stop the test.

        :param test: The test as a function.
        """

        # Create the avatar.
        self._create_avatar(avatar_id=self.id, debug=True)
        # Run the test.
        test()
        # End the test.
        self._destroy_avatar(avatar_id=self.id)

    def symmetry(self) -> None:
        """
        Test: Both arms raise symmetrically.
        """

        self.bend_arm(avatar_id=self.id, target={"x": -0.2, "y": 0.4, "z": 0.385}, arm=Arm.left)
        self.bend_arm(avatar_id=self.id, target={"x": 0.2, "y": 0.4, "z": 0.385}, arm=Arm.right)

    def rotation(self) -> None:
        """
        Test: The IK target follows the rotation of the avatar.
        """

        d_theta = 15
        theta = 15
        while theta < 360:
            self.communicate({"$type": "rotate_avatar_by",
                              "angle": theta,
                              "axis": "yaw",
                              "is_world": True,
                              "avatar_id": self.id})

            self.bend_arm(avatar_id=self.id, target={"x": -0.4, "y": 0.3, "z": 0.185}, arm=Arm.left)
            self.bend_arm(avatar_id=self.id, target={"x": 0.4, "y": 0.3, "z": 0.185}, arm=Arm.right)
            self.reset_arms(avatar_id=self.id)
            theta += d_theta

    def position(self) -> None:
        """
        Test: The IK target follows the position of the avatar.
        """

        self.communicate({"$type": "teleport_avatar_to",
                          "position": {"x": 1.1, "y": 0.0, "z": 1},
                          "avatar_id": self.id})
        self.bend_arm(avatar_id=self.id, target={"x": -0.2, "y": 0.4, "z": 0.385}, arm=Arm.left)

    def pick_up_test(self) -> None:
        """
        Test: The avatar picks up the object. The avatar is at a non-origin position and rotation.
        """

        o_id = self.get_unique_id()
        self.communicate([{"$type": "teleport_avatar_to",
                           "position": {"x": 1.1, "y": 0.0, "z": 1},
                           "avatar_id": self.id},
                          {"$type": "rotate_avatar_by",
                           "angle": -45,
                           "axis": "yaw",
                           "is_world": True,
                           "avatar_id": self.id}])
        self.communicate(self._add_object("jug05",
                                          position={"x": 0.9, "y": 0, "z": 1.385},
                                          object_id=o_id,
                                          scale={"x": 0.8, "y": 0.8, "z": 0.8}))
        self.pick_up(avatar_id=self.id, object_id=o_id)
        assert o_id in self._avatars[self.id].frame.get_held_right()


if __name__ == "__main__":
    c = IKUnitTests()
    c.init_scene()
    c.do_test(c.symmetry)
    c.do_test(c.rotation)
    c.do_test(c.position)
    c.do_test(c.pick_up_test)
    c.end()
