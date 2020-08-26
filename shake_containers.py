from sticky_mitten_avatar.avatars import Arm
from sticky_mitten_avatar import StickyMittenAvatarController


class ShakeContainer(StickyMittenAvatarController):
    def __init__(self, port: int = 1071, launch_build: bool = True):
        super().__init__(port=port, launch_build=launch_build, audio_playback_mode="unity")

    def run(self):
        # Initialize the scene.
        commands = [self.get_add_scene(scene_name="box_room_2018"),
                    {"$type": "set_aperture",
                     "aperture": 4.8},
                    {"$type": "set_focus_distance",
                     "focus_distance": 1.25},
                    {"$type": "set_post_exposure",
                     "post_exposure": 0.4},
                    {"$type": "set_ambient_occlusion_intensity",
                     "intensity": 0.175},
                    {"$type": "set_ambient_occlusion_thickness_modifier",
                     "thickness": 3.5}]
        # Add the objects.
        sofa_id = self.get_unique_id()
        container_id_0 = self.get_unique_id()
        container_id_1 = self.get_unique_id()
        # Add the containers.
        commands.extend(self.get_add_container(model_name="shoebox_fused",
                                               object_id=container_id_0,
                                               contents=["sphere", "sphere"],
                                               position={"x": -3.068, "y": 0, "z": 0.764},
                                               rotation={"x": 0, "y": 13, "z": 0}))
        commands.extend(self.get_add_container(model_name="shoebox_fused",
                                               object_id=container_id_1,
                                               contents=["cone", "cone", "cone", "cone"],
                                               position={"x": -4.033, "y": 0, "z": 1.228},
                                               rotation={"x": 0, "y": 55, "z": 0}))
        # Add the sofa.
        commands.extend(self.get_add_object(model_name="napoleon_iii_sofa",
                                            object_id=sofa_id,
                                            position={"x": -4.97, "y": 0, "z": 2.14},
                                            rotation={"x": 0, "y": 93, "z": 0}))
        # Populate the room with other objects.
        commands.extend(self.get_add_object(model_name="alma_floor_lamp",
                                            object_id=self.get_unique_id(),
                                            position={"x": -4.78, "y": 0, "z": 3.4},
                                            rotation={"x": 0, "y": 90, "z": 0}))
        commands.extend(self.get_add_object(model_name="blue_side_chair",
                                            object_id=self.get_unique_id(),
                                            position={"x": -4.91, "y": 0, "z": 0.483},
                                            rotation={"x": 0, "y": 80, "z": 0}))
        commands.extend(self.get_add_object(model_name="rh10",
                                            object_id=self.get_unique_id(),
                                            position={"x": -3.42, "y": 0, "z": -0.119},
                                            rotation={"x": 0, "y": 33, "z": 0}))
        commands.extend(self.get_add_object(model_name="sm_table_white",
                                            object_id=self.get_unique_id(),
                                            position={"x": -2.535, "y": 0, "z": 3.4},
                                            rotation={"x": 0, "y": 0, "z": 0}))
        commands.extend(self.get_add_object(model_name="vitra_meda_chair",
                                            object_id=self.get_unique_id(),
                                            position={"x": -2.618, "y": 0, "z": 2.504},
                                            rotation={"x": 0, "y": -28, "z": 0}))
        commands.extend(self.get_add_object(model_name="macbook_air",
                                            object_id=self.get_unique_id(),
                                            position={"x": -2.535, "y": 0.902, "z": 3.4},
                                            rotation={"x": 0, "y": 170, "z": 0},
                                            scale={"x": 1.2, "y": 1.2, "z": 1.2}))
        self.communicate(commands)
        # Add the avatar and the camera.
        avatar_id = "a"
        self.create_avatar(avatar_id=avatar_id,
                           position={"x": -3.661998, "y": 0, "z": 0.507},
                           rotation=60)
        # Low-level
        cam_id = "c"
        self.add_overhead_camera(position={"x": -2.369, "y": 0.582, "z": 1.651},
                                 target_object=avatar_id,
                                 images="cam",
                                 cam_id=cam_id)

        self.end_scene_setup()

        # Pick up the first container. Shake it, and put it down.
        self.go_to(avatar_id=avatar_id, target=container_id_0)
        self.pick_up(avatar_id=avatar_id, object_id=container_id_0)
        self.bend_arm(avatar_id=avatar_id, target={"x": 0.3, "y": 0.4, "z": 0.285}, arm=Arm.left, absolute=False)
        self.shake(avatar_id=avatar_id, joint_name=f"elbow_left")
        self.put_down(avatar_id=avatar_id, do_motion=False)

        # Pick up the second container. Shake it, and put it down.
        self.go_to(avatar_id=avatar_id, target=container_id_1)
        self.pick_up(avatar_id=avatar_id, object_id=container_id_1)
        self.bend_arm(avatar_id=avatar_id, target={"x": -0.3, "y": 0.4, "z": 0.285}, arm=Arm.right, absolute=False)
        self.shake(avatar_id=avatar_id, joint_name=f"elbow_right")
        self.put_down(avatar_id=avatar_id, do_motion=False)

        # Pick up the first container again.
        self.go_to(avatar_id=avatar_id, target=container_id_0)
        self.pick_up(avatar_id=avatar_id, object_id=container_id_0)
        self.bend_arm(avatar_id=avatar_id, target={"x": 0.3, "y": 0.4, "z": 0.285}, arm=Arm.left, absolute=False)

        # Go to the sofa.
        self.go_to(avatar_id=avatar_id, target={"x": -4.475, "y": 0, "z": 2.132})

        # Put the container on the sofa.
        self.bend_arm(avatar_id=avatar_id, target={"x": -4.75, "y": 0.9, "z": 1.885}, arm=Arm.left, absolute=True)
        self.put_down(avatar_id=avatar_id, do_motion=False)
        for i in range(100):
            self.communicate([])


if __name__ == "__main__":
    ShakeContainer(launch_build=False).run()
