import numpy as np
from distutils import dir_util
from pathlib import Path
from typing import Tuple, List, Optional, Union
from tdw.controller import Controller
from tdw.tdw_utils import TDWUtils
from tdw.output_data import OutputData, AvatarChildrenNames, AvatarStickyMitten, Images, Bounds


class PutObjectOnTable(Controller):
    OUTPUT_DIR = Path("images")
    # Remove the previous images.
    if OUTPUT_DIR.exists():
        dir_util.remove_tree(str(OUTPUT_DIR.resolve()))
    OUTPUT_DIR.mkdir(parents=True)
    OUTPUT_DIR = str(OUTPUT_DIR.resolve())

    def __init__(self, check_version: bool = True, launch_build: bool = True):
        super().__init__(check_version=check_version, launch_build=launch_build)

        self.avatar_position: Tuple[float, float, float] = (0, 0, 0)
        self.frame_number = 0
        # Camera ID.
        self.cam_id = "c"

    def run(self):
        self.start()

        # Get IDs for the object, the table, and the avatars.
        o_id = self.get_unique_id()
        table_id = self.get_unique_id()
        table_position = {"x": 0, "y": 0, "z": 6.8}
        a = "a"

        # 1. Create the room.
        commands = [TDWUtils.create_empty_room(20, 20)]
        # 2. Add the avatar.
        commands.extend(TDWUtils.create_avatar(avatar_type="A_StickyMitten_Adult",
                                               avatar_id="a"))
        # 3. Add the objects. Scale the objects. Set a high mass for the table.
        # 4. Disable the avatar's cameras.
        # 5. Set the stickiness of the avatar's left mitten. Set a high drag. Rotate the head.
        # 6. Request AvatarChildrenNames data and Bounds data (this frame only).
        commands.extend([self.get_add_object("jug05",
                                             position={"x": -0.417, "y": 0.197, "z": 0.139},
                                             rotation={"x": 90, "y": 0, "z": 0},
                                             object_id=o_id),
                         {"$type": "scale_object",
                          "scale_factor": {"x": 2.5, "y": 2.5, "z": 2.5},
                          "id": o_id},
                         self.get_add_object("small_table_green_marble",
                                             position={"x": 0, "y": 0, "z": 6.8},
                                             rotation={"x": 0, "y": 0, "z": 0},
                                             object_id=table_id),
                         {"$type": "scale_object",
                          "scale_factor": {"x": 2, "y": 0.5, "z": 2},
                          "id": table_id},
                         {"$type": "set_mass",
                          "mass": 100,
                          "id": table_id},
                         {"$type": "toggle_image_sensor",
                          "sensor_name": "SensorContainer",
                          "avatar_id": a},
                         {"$type": "toggle_image_sensor",
                          "sensor_name": "FollowCamera",
                          "avatar_id": a},
                         {"$type": "set_stickiness",
                          "sub_mitten": "back",
                          "sticky": True,
                          "is_left": True,
                          "avatar_id": a},
                         {"$type": "set_avatar_drag",
                          "drag": 0.125,
                          "angular_drag": 1000,
                          "avatar_id": a},
                         {"$type": "rotate_head_by",
                          "axis": "pitch",
                          "angle": 25},
                         {"$type": "send_avatar_children_names",
                          "ids": [a],
                          "frequency": "once"},
                         {"$type": "send_bounds",
                          "ids": [table_id],
                          "frequency": "once"}])
        # 7. Add a 3rd-person camera.
        commands.extend(TDWUtils.create_avatar(avatar_type="A_Img_Caps_Kinematic",
                                               avatar_id="c",
                                               position={"x": 3.9, "y": 2.3, "z": 4.3}))
        # 8. Request StickyMittenAvatar and Images data per-frame.
        commands.extend([{"$type": "set_pass_masks",
                          "pass_masks": ["_img"],
                          "avatar_id": self.cam_id},
                         {"$type": "send_avatars",
                          "ids": [a],
                          "frequency": "always"},
                         {"$type": "send_images",
                          "ids": [self.cam_id],
                          "frequency": "always"}])

        resp = self.communicate(commands)
        # Get the object ID of the left mitten, the size of the table, and the avatar's position.
        mitten_left_id = None
        table_size: Tuple[float, float, float] = (0, 0, 0)

        for r in resp[:-1]:
            r_id = OutputData.get_data_type_id(r)
            # Get the mitten ID.
            if r_id == "avcn":
                avcn = AvatarChildrenNames(r)
                for i in range(avcn.get_num_children()):
                    if avcn.get_child_name(i) == "mitten_left":
                        mitten_left_id = avcn.get_child_id(i)
            # Get the table bounds.
            elif r_id == "boun":
                boun = Bounds(r)
                for i in range(boun.get_num()):
                    if boun.get_id(i) == table_id:
                        table_size = (boun.get_right(i)[0] - boun.get_left(i)[0],
                                      boun.get_top(i)[1] - boun.get_bottom(i)[1],
                                      boun.get_front(i)[2] - boun.get_back(i)[2])
            # Get the avatar's position.
            elif r_id == "avsm":
                self.avatar_position = AvatarStickyMitten(r).get_position()

        # Pick up the object.
        self._do_frame({"$type": "pick_up_proximity",
                        "distance": 20,
                        "grip": 10000,
                        "is_left": True,
                        "avatar_id": a})

        # Move to the table.
        move_to_table = True
        # The position of the side of the table the avatar is aiming for.
        table_side_position = {"x": table_position["x"], "y": 0, "z": table_position["z"] - table_size[2]}
        while move_to_table:
            # Stop moving if we are close enough.
            if TDWUtils.get_distance(table_side_position, TDWUtils.array_to_vector3(self.avatar_position)) < 3:
                move_to_table = False
            # Keep moving forward.
            else:
                self._do_frame({"$type": "move_avatar_forward_by",
                                "avatar_id": a,
                                "magnitude": 50})
        # Stop the avatar.
        stopped = False
        while not stopped:
            avsm = self._do_frame({"$type": "move_avatar_forward_by",
                                   "avatar_id": a,
                                   "magnitude": -55})
            stopped = np.linalg.norm(avsm.get_velocity()) <= 2
        # Let the avatar coast to a stop.
        stopped = False
        while not stopped:
            avsm = self._do_frame([])
            stopped = np.linalg.norm(avsm.get_velocity()) <= 0.01

    def _do_frame(self, commands: Union[List[dict], dict]) -> AvatarStickyMitten:
        """
        Send commands to the build. Receive images and sticky mitten avatar data.
        Save the images.

        :param commands: The commands for this frame.

        :return: The avatar data.
        """

        # Add to the list of commands: Look at the avatar.
        frame_commands = [{"$type": "look_at_position",
                           "position": {"x": self.avatar_position[0],
                                        "y": self.avatar_position[1] + 0.5,
                                        "z": self.avatar_position[2]},
                           "avatar_id": self.cam_id}]

        if isinstance(commands, dict):
            frame_commands.append(commands)
        else:
            frame_commands.extend(commands)

        resp = self.communicate(frame_commands)

        avsm: Optional[AvatarStickyMitten] = None
        for r in resp[:-1]:
            r_id = OutputData.get_data_type_id(r)
            # Save images.
            if r_id == "imag":
                TDWUtils.save_images(images=Images(r),
                                     filename=TDWUtils.zero_padding(self.frame_number, 4),
                                     output_directory=PutObjectOnTable.OUTPUT_DIR)
            elif r_id == "avsm":
                avsm = AvatarStickyMitten(r)
        # Update the position of the avatar and the frame number.
        self.avatar_position = avsm.get_position()
        self.frame_number += 1
        return avsm


"""
        self.communicate()

        # Add the avatar and the object.
        self.communicate()
        o_id =

        # 1. Disable the SensorContainer to ensure that the FollowCamera will render to the screen.
        # 2. Scale the object to be more visible.
        # 3. Set the back of the left mitten as "sticky".
        # 4. Set a high angular drag for the avatar to ensure that it won't spin like a top.
        # 5. Rotate the head to look down at the object.
        # 6. Pick up the object. Set a high grip to ensure that the avatar won't drop the object.
        # 7. Bend the arm joints.
        #
        # NOTE: We don't specify avatar_id because the default is "a",
        #       which is what TDWUtils.create_avatar sets it to.
        self.communicate([


                          
                          {"$type": "pick_up_proximity",
                           "distance": 20,
                           "grip": 10000,
                           "is_left": True},
                          {"$type": "bend_arm_joint_by",
                           "angle": 25,
                           "joint": "shoulder_left",
                           "axis": "pitch"},
                          {"$type": "bend_arm_joint_by",
                           "angle": -25,
                           "joint": "shoulder_left",
                           "axis": "yaw"},
                          {"$type": "bend_arm_joint_by",
                           "angle": 60,
                           "joint": "shoulder_left",
                           "axis": "roll"},
                          {"$type": "bend_arm_joint_by",
                           "angle": 100,
                           "joint": "elbow_left",
                           "axis": "pitch"},
                          {"$type": "bend_arm_joint_by",
                           "angle": 15,
                           "joint": "shoulder_right",
                           "axis": "pitch"},
                          {"$type": "bend_arm_joint_by",
                           "angle": -15,
                           "joint": "shoulder_right",
                           "axis": "yaw"},
                          {"$type": "bend_arm_joint_by",
                           "angle": 35,
                           "joint": "elbow_right",
                           "axis": "pitch"}])

        # Let the simulation run for a while to allow the arm joints to bend.
        for i in range(100):
            self.communicate([])
        # Move the avatar forward.
        for i in range(20):
            self.communicate({"$type": "move_avatar_forward_by",
                              "magnitude": 50})
        for i in range(100):
            self.communicate([])
        # Drop the object and bend the joints down.
        self.communicate([{"$type": "rotate_head_by",
                           "axis": "pitch",
                           "angle": 0},
                          {"$type": "put_down",
                           "is_left": True},
                          {"$type": "bend_arm_joint_to",
                           "angle": 0,
                           "joint": "shoulder_left",
                           "axis": "pitch"},
                          {"$type": "bend_arm_joint_to",
                           "angle": 0,
                           "joint": "shoulder_left",
                           "axis": "yaw"},
                          {"$type": "bend_arm_joint_to",
                           "angle": 0,
                           "joint": "shoulder_left",
                           "axis": "roll"},
                          {"$type": "bend_arm_joint_to",
                           "angle": 0,
                           "joint": "elbow_left",
                           "axis": "pitch"},
                          {"$type": "bend_arm_joint_to",
                           "angle": 0,
                           "joint": "shoulder_right",
                           "axis": "pitch"},
                          {"$type": "bend_arm_joint_to",
                           "angle": 0,
                           "joint": "shoulder_right",
                           "axis": "yaw"},
                          {"$type": "bend_arm_joint_to",
                           "angle": 0,
                           "joint": "elbow_right",
                           "axis": "pitch"}])
        for i in range(100):
            self.communicate([])


if __name__ == "__main__":
    StickyMittenAvatar().run()
"""
if __name__ == "__main__":
    PutObjectOnTable(launch_build=False, check_version=False).run()