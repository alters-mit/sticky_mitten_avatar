from pathlib import Path
import numpy as np
from typing import Union, List, Optional, Tuple
from tdw.tdw_utils import TDWUtils
from tdw.output_data import OutputData, Images
from sticky_mitten_avatar import StickyMittenAvatarController, Arm
from sticky_mitten_avatar.task_status import TaskStatus


class DemoVideo(StickyMittenAvatarController):
    """
    Use this controller to create a demo video.
    This uses many low-level TDW functions and commands and is NOT meant to be an example of an average use-case.
    """

    _D_THETA_GRASP = 15

    def __init__(self, port: int = 1071, launch_build: bool = True):
        super().__init__(port=port, launch_build=launch_build, demo=True, id_pass=False, screen_width=1024,
                         screen_height=1024, debug=False)
        self.cam_id = "c"

        self.cam_absolute_y = 4.75
        self.cam_relative_x = -1.3
        self.cam_relative_z = 0.75
        self.cam_fov = 40

        self.image_count = 0
        self.output_directory = ""

    def _get_scene_init_commands(self, scene: str = None, layout: int = None, room: int = -1,
                                 target_objects_room: int = -1) -> List[dict]:
        commands = super()._get_scene_init_commands(scene=scene, layout=layout, room=room,
                                                    target_objects_room=target_objects_room)
        # Make NavMesh obstacles.
        nav_obstacle_commands = []
        for cmd in commands:
            if cmd["$type"] == "set_kinematic_state" and not cmd["is_kinematic"]:
                nav_obstacle_commands.append({"$type": "make_nav_mesh_obstacle",
                                              "id": cmd["id"],
                                              "carve_type": "stationary",
                                              "scale": 0.5})
        commands.extend(nav_obstacle_commands)

        # Create the 3rd-person camera.
        commands.extend(TDWUtils.create_avatar(position={"x": 0, "y": self.cam_absolute_y, "z": 0},
                                               avatar_id=self.cam_id))
        # Set the field of view of the 3rd-person camera.
        # Enable the follow camera.
        # Hide the roof.
        commands.extend([{"$type": "set_field_of_view",
                          "field_of_view": self.cam_fov,
                          "avatar_id": self.cam_id},
                         {"$type": "enable_image_sensor",
                          "enable": True,
                          "sensor_name": "FollowCamera",
                          "avatar_id": "a"},
                         {"$type": "set_floorplan_roof",
                          "show": False},
                         {"$type": "set_pass_masks",
                          "pass_masks": ["_img"],
                          "avatar_id": self.cam_id},
                         {"$type": "set_pass_masks",
                          "pass_masks": ["_img"],
                          "avatar_id": "a"}])

        # Enable image capture.
        self._cam_commands = [{"$type": "look_at_avatar",
                               "target_avatar_id": "a",
                               "avatar_id": self.cam_id},
                              {"$type": "send_images",
                               "frequency": "once"}]
        return commands

    def communicate(self, commands: Union[dict, List[dict]]) -> List[bytes]:
        resp = super().communicate(commands)

        # Make the camera follow the avatar.
        if self._avatar is not None:
            avatar_position = TDWUtils.array_to_vector3(self._avatar.frame.get_position())
            avatar_position["y"] = self.cam_absolute_y
            avatar_position["x"] += self.cam_relative_x
            avatar_position["z"] += self.cam_relative_z
            self._avatar_commands.extend([{"$type": "teleport_avatar_to",
                                           "position": avatar_position,
                                           "avatar_id": self.cam_id}])
        # Save images.
        any_images = False
        for i in range(len(resp) - 1):
            r_id = OutputData.get_data_type_id(resp[i])
            if r_id == "imag":
                any_images = True
                images = Images(resp[i])
                TDWUtils.save_images(images=images, filename=TDWUtils.zero_padding(self.image_count, width=5),
                                     output_directory=str(Path(self.output_directory).
                                                          joinpath(images.get_avatar_id(),
                                                                   images.get_sensor_name()).resolve()))
        if any_images:
            self.image_count += 1
        return resp

    def _lift_arm(self, arm: Arm) -> None:
        """
        Lift the arm up.

        :param arm: The arm.
        """

        self.reach_for_target(arm=arm,
                              target={"x": -0.2 if arm == Arm.left else 0.2, "y": 0.4, "z": 0.3},
                              check_if_possible=False,
                              stop_on_mitten_collision=False)

    def grasp_and_lift(self, object_id: int, arm: Optional[Arm] = None) -> bool:
        """
        Repeatedly try to grasp a nearby object. If the object was grasped, lift it up.

        :param object_id: The ID of the target object.
        :param arm: Set the arm that should grasp and lift.

        :return: Tuple: True if the avatar grasped the object; the number of actions the avatar did.
        """

        def _turn_to_grasp(direction: int) -> bool:
            """
            Turn a bit, then try to grasp the object.
            This ends when the avatar has turned too far or if it grasps the object.

            :param direction: The direction to turn.

            :return: True if the avatar grasped the object.
            """

            theta = 0
            grasp_arm: Optional[Arm] = None
            # Try turning before giving up.
            # You can try adjusting this maximum.
            while theta < 90 and grasp_arm is None:
                # Try to grasp the object with each arm.
                for a in [Arm.left, Arm.right]:
                    if arm is not None and a != arm:
                        continue
                    s = self.grasp_object(object_id=object_id, arm=a)
                    if s == TaskStatus.success:
                        grasp_arm = a
                        break
                    else:
                        self.reset_arm(arm=a)
                if grasp_arm is None:
                    # Try turning some more.
                    s = self.turn_by(self._D_THETA_GRASP * direction)
                    # Failed to turn.
                    if s != TaskStatus.success:
                        return False
                    theta += self._D_THETA_GRASP
            if grasp_arm is not None:
                self._lift_arm(arm=grasp_arm)
            return grasp_arm is not None

        object_id = int(object_id)

        # Turn to face the object.
        self.turn_to(target=object_id)

        if arm is not None and arm == Arm.right:
            d = -1
        else:
            d = 1

        # Turn and grasp repeatedly.
        success = _turn_to_grasp(d)
        if success:
            return True

        # Reset the rotation.
        status = self.turn_by(-90)
        if status != TaskStatus.success:
            return False

        # Try turning the other way.
        d *= -1
        success = _turn_to_grasp(d)
        return success

    def _go_to_and_lift(self, object_id: int, stopping_distance: float, arm: Arm = None) -> \
            Tuple[TaskStatus, int]:
        """
        Go to a random object. Try to grasp it and lift it up.

        :param object_id: The ID of the object.
        :param arm: If not None, the specified arm will try to grasp the object.
        :param stopping_distance:  Stop at this distance from the object.

        :return: Tuple: TaskStatus, and the object ID.
        """

        # Go to the object.
        self.go_to(object_id, move_stopping_threshold=stopping_distance)

        # Correct for a navigation error.
        d = np.linalg.norm(self.frame.avatar_transform.position - self.frame.object_transforms[object_id].position)
        for i in range(5):
            if d > 0.7:
                self.go_to(object_id, move_stopping_threshold=stopping_distance)
            else:
                break
        # Pick up the object.
        success = self.grasp_and_lift(object_id=object_id, arm=arm)

        return TaskStatus.success if success else TaskStatus.failed_to_pick_up, object_id

    def _get_container_id(self) -> int:
        """
        :return: The ID of a random container.
        """

        for object_id in self.static_object_info:
            if self.static_object_info[object_id].container:
                return int(object_id)
        raise Exception("No container found. Re-run this controller.")

    def navigation(self) -> None:
        self.output_directory = "D:/sticky_mitten_avatar_demo/navigation"
        self.init_scene(scene="2a", layout=1, room=3, target_objects_room=4)

        # Teleport a container to a nearby position.
        container_id = self._get_container_id()
        container_position = {"x": 0.1, "y": 0, "z": 2.1}
        self.communicate({"$type": "teleport_object",
                          "id": container_id,
                          "position": container_position})
        self.go_to(target={"x": -1.35, "y": 0, "z": 2.3})
        self.turn_to(target=container_id)
        self._go_to_and_lift(object_id=container_id, stopping_distance=0.3)

        # Go to each point on the path.
        for p in [[0.1, 0, 0.66], [0.4, 0, 0.46], [4.3, 0, 0.13], [4.35, 0, -1.1], [4.3, 0, -1.4]]:
            self.go_to(target=TDWUtils.array_to_vector3(p))
        if len(self.frame.held_objects[Arm.left]) > 0:
            object_arm = Arm.right
        else:
            object_arm = Arm.left

        # Put objects in the container.
        for target_object_id in self._target_object_ids[:2]:
            self._go_to_and_lift(object_id=target_object_id, arm=object_arm, stopping_distance=0.3)
            self.put_in_container(object_id=target_object_id, container_id=container_id, arm=object_arm)
        self.end()

    def collisions(self) -> None:
        self.output_directory = "D:/sticky_mitten_avatar_demo/collisions"
        self.init_scene(scene="2a", layout=1, room=4, target_objects_room=4)
        container_id = self._get_container_id()
        self.communicate({"$type": "teleport_object",
                          "id": container_id,
                          "position": {"x": 6.03, "y": 0, "z": -1.49}})

        # Send the avatar to bad destinations before finally picking up the container.
        for position in [[8.26, 0, -5.32], [9.12, 0, -3.1], [5.67, 0, -0.46]]:
            self.go_to(target=TDWUtils.array_to_vector3(position))
            # Back up a bit.
            self.move_forward_by(distance=-0.5)
        # Go to the container and pick it up.
        self._go_to_and_lift(object_id=container_id, stopping_distance=0.3)
        self.move_forward_by(1)
        self.end()


if __name__ == "__main__":
    c = DemoVideo()
    c.collisions()
    # c.navigation()
