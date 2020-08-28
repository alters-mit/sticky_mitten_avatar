from typing import List
from sticky_mitten_avatar import StickyMittenAvatarController


class BoxRoomContainers(StickyMittenAvatarController):
    """
    A simple room with some furniture, props, and two containers with objects in them.

    Enables audio playback.
    """

    def __init__(self, port: int = 1071, launch_build: bool = True):
        super().__init__(port=port, launch_build=launch_build, audio_playback_mode="unity")
        self.avatar_id = "a"
        self.container_0 = self.get_unique_id()
        self.container_1 = self.get_unique_id()

    def _get_scene_init_commands_early(self) -> List[dict]:
        # Load the scene.
        commands = [self.get_add_scene(scene_name="box_room_2018")]
        # Add objects.
        commands.extend(self.get_add_object("woven_box",
                                            position={"x": 3.37, "y": 0, "z": -2.56},
                                            object_id=self.get_unique_id()))
        commands.extend(self.get_add_object("trapezoidal_table",
                                            position={"x": 0.491, "y": 0, "z": 0},
                                            rotation={"x": 180.0, "y": 90.0, "z": 180.0},
                                            object_id=self.get_unique_id()))
        commands.extend(self.get_add_object("rh10",
                                            position={"x": 3.408, "y": 0, "z": -0.153},
                                            rotation={"x": 0.0, "y": 80, "z": 0.0},
                                            object_id=self.get_unique_id()))
        commands.extend(self.get_add_object("satiro_sculpture",
                                            position={"x": 0.632, "y": 0.36043, "z": 0.23},
                                            rotation={"x": 0, "y": 90, "z": 0},
                                            scale={"x": 0.3, "y": 0.3, "z": 0.3},
                                            object_id=self.get_unique_id()))
        commands.extend(self.get_add_object("vitra_meda_chair",
                                            position={"x": 4.28, "y": 0, "z": -1.61},
                                            rotation={"x": 0.0, "y": -60, "z": 0.0},
                                            object_id=self.get_unique_id()))
        commands.extend(self.get_add_object("trunck",
                                            position={"x": 4.377, "y": 0, "z": 0.804},
                                            rotation={"x": 0, "y": 15, "z": 0},
                                            object_id=self.get_unique_id()))
        commands.extend(self.get_add_object("live_edge_coffee_table",
                                            position={"x": 2.195, "y": 0, "z": 1.525},
                                            scale={"x": 1, "y": 1, "z": 1.35},
                                            object_id=self.get_unique_id()))
        commands.extend(self.get_add_object("sayonara_sofa",
                                            position={"x": 2.588, "y": 0, "z": 2.513},
                                            rotation={"x": 180.0, "y": 0.0, "z": 180.0},
                                            object_id=2544507))
        commands.extend(self.get_add_object("small_table_green_marble",
                                            position={"x": -0.248, "y": 0, "z": -4.334},
                                            object_id=5258547))
        commands.extend(self.get_add_object("arflex_hollywood_sofa",
                                            position={"x": 0.567, "y": 0, "z": -2.153},
                                            object_id=5922932))
        commands.extend(self.get_add_object("macbook_air",
                                            position={"x": 2.024, "y": 0.46, "z": -2.399},
                                            object_id=1453018))
        commands.extend(self.get_add_object("alma_floor_lamp",
                                            position={"x": 3.637, "y": 0, "z": 2.45},
                                            object_id=9067846))
        commands.extend(self.get_add_object("duffle_bag",
                                            position={"x": 2.213, "y": 0, "z": -1.578},
                                            rotation={"x": 0.0, "y": 29.550001010645264, "z": 0.0},
                                            object_id=7313859))

        # Add the containers.
        commands.extend(self.get_add_container(model_name="shoebox_fused",
                                               object_id=self.container_0,
                                               contents=["sphere", "sphere"],
                                               position={"x": 0.771, "y": 0.3711542, "z": -0.385},
                                               rotation={"x": 0, "y": 13, "z": 0}))
        commands.extend(self.get_add_container(model_name="shoebox_fused",
                                               object_id=self.container_1,
                                               contents=["cone", "cone", "cone", "cone"],
                                               position={"x": 1.584, "y": 0.3359459, "z": 1.34},
                                               rotation={"x": 0, "y": 55, "z": 0}))

        commands.extend([{"$type": "set_aperture",
                          "aperture": 8.0},
                         {"$type": "set_focus_distance",
                          "focus_distance": 2.25},
                         {"$type": "set_post_exposure",
                          "post_exposure": 0.4},
                         {"$type": "set_ambient_occlusion_intensity",
                          "intensity": 0.175},
                         {"$type": "set_ambient_occlusion_thickness_modifier",
                          "thickness": 3.5},
                         {"$type": "step_physics",
                          "frames": 300}])
        return commands

    def _do_scene_init_late(self) -> None:
        cam_id = "c"
        self.add_overhead_camera(position={"x": 2.315, "y": 1.6, "z": -0.474},
                                 target_object=self.avatar_id,
                                 images="cam",
                                 cam_id=cam_id)
        self.communicate({"$type": "set_field_of_view",
                          "field_of_view": 60.0,
                          "avatar_id": cam_id})

    def _init_avatar(self) -> None:
        self.create_avatar(avatar_id=self.avatar_id,
                           rotation=-15,
                           position={"x": 1.385, "y": 0, "z": -0.95})
