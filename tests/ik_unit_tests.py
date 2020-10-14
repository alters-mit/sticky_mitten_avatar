from tdw.tdw_utils import TDWUtils
from sticky_mitten_avatar.avatars import Arm
from sticky_mitten_avatar import StickyMittenAvatarController
from sticky_mitten_avatar.task_status import TaskStatus
from sticky_mitten_avatar.util import rotate_point_around, get_angle_between, FORWARD


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

        status = self.reach_for_target(target={"x": -0.2, "y": 0.4, "z": 0.385}, arm=Arm.left)
        assert status == TaskStatus.success, status
        status = self.reach_for_target(target={"x": 0.2, "y": 0.4, "z": 0.385}, arm=Arm.right)
        assert status == TaskStatus.success, status

    def rotation(self) -> None:
        """
        Test: The IK target follows the rotation of the avatar.
        """

        d_theta = 15
        theta = 15
        while theta < 360:
            self.communicate({"$type": "rotate_avatar_by",
                              "angle": d_theta,
                              "axis": "yaw",
                              "is_world": True,
                              "avatar_id": self.id})

            status = self.reach_for_target(target={"x": -0.2, "y": 0.4, "z": 0.385}, arm=Arm.left)
            assert status == TaskStatus.success, status
            status = self.reset_arm(arm=Arm.left)
            assert status == TaskStatus.success, status
            status = self.reach_for_target(target={"x": 0.2, "y": 0.4, "z": 0.385}, arm=Arm.right)
            assert status == TaskStatus.success, status
            status = self.reset_arm(arm=Arm.right)
            assert status == TaskStatus.success, status
            theta += d_theta

    def position(self) -> None:
        """
        Test: The IK target follows the position of the avatar.
        """

        self.communicate({"$type": "teleport_avatar_to",
                          "position": {"x": 1.1, "y": 0.0, "z": 1},
                          "avatar_id": self.id})
        status = self.reach_for_target(target={"x": -0.2, "y": 0.4, "z": 0.385}, arm=Arm.left)
        assert status == TaskStatus.success, status

    def pick_up_test(self) -> None:
        """
        Test: The avatar picks up the object. The avatar is at a non-origin position and rotation.
        """

        self.communicate([{"$type": "teleport_avatar_to",
                           "position": {"x": 1.1, "y": 0.0, "z": 1},
                           "avatar_id": self.id},
                          {"$type": "rotate_avatar_by",
                           "angle": -45,
                           "axis": "yaw",
                           "is_world": True,
                           "avatar_id": self.id}])
        o_id, jug_commands = self._add_object("jug05",
                                              position={"x": 1.05, "y": 0, "z": 1.245},
                                              scale={"x": 0.8, "y": 0.8, "z": 0.8})
        self.communicate(jug_commands)
        status = self.grasp_object(object_id=o_id, arm=Arm.right)
        assert status == TaskStatus.success, status


if __name__ == "__main__":
    c = IKUnitTests()
    c.init_scene()

    c.do_test(c.symmetry)
    c.do_test(c.rotation)
    c.do_test(c.position)
    c.do_test(c.pick_up_test)
    c.end()
