from sticky_mitten_avatar.task_status import TaskStatus
from typing import List
from sticky_mitten_avatar import StickyMittenAvatarController, Arm


class BoxRoomContainers(StickyMittenAvatarController):
    """
    A demo of an avatar shaking boxes. Each box has a different number of objects.
    Each group of objects has a different audio material. The avatar will shake each box and then "decide" which box to
    put on the sofa.
    """

    def __init__(self, port: int = 1071, launch_build: bool = False, demo: bool = False):
        super().__init__(port=port, launch_build=launch_build, demo=demo)
        self.avatar_id = "a"
        self.container_0 = 0
        self.container_1 = 1

    def _get_scene_init_commands(self, scene: str = None, layout: int = None) -> List[dict]:
        # Load the scene.
        commands = [self.get_add_scene(scene_name="box_room_2018")]
        # Add objects.
        commands.extend(self._add_object("woven_box",
                                         position={"x": 3.37, "y": 0, "z": -2.56})[1])
        commands.extend(self._add_object("trapezoidal_table",
                                         position={"x": 0.491, "y": 0, "z": 0},
                                         rotation={"x": 180.0, "y": 90.0, "z": 180.0})[1])
        commands.extend(self._add_object("rh10",
                                         position={"x": 3.408, "y": 0, "z": -0.153},
                                         rotation={"x": 0.0, "y": 80, "z": 0.0})[1])
        commands.extend(self._add_object("satiro_sculpture",
                                         position={"x": 0.632, "y": 0.36043, "z": 0.23},
                                         rotation={"x": 0, "y": 90, "z": 0},
                                         scale={"x": 0.3, "y": 0.3, "z": 0.3})[1])
        commands.extend(self._add_object("vitra_meda_chair",
                                         position={"x": 4.28, "y": 0, "z": -1.61},
                                         rotation={"x": 0.0, "y": -60, "z": 0.0})[1])
        commands.extend(self._add_object("trunck",
                                         position={"x": 4.377, "y": 0, "z": 0.804},
                                         rotation={"x": 0, "y": 15, "z": 0})[1])
        commands.extend(self._add_object("live_edge_coffee_table",
                                         position={"x": 2.195, "y": 0, "z": 1.525},
                                         scale={"x": 1, "y": 1, "z": 1.35})[1])
        commands.extend(self._add_object("sayonara_sofa",
                                         position={"x": 2.588, "y": 0, "z": 2.513},
                                         rotation={"x": 180.0, "y": 0.0, "z": 180.0})[1])
        commands.extend(self._add_object("small_table_green_marble",
                                         position={"x": -0.248, "y": 0, "z": -4.334})[1])
        commands.extend(self._add_object("arflex_hollywood_sofa",
                                         position={"x": 0.567, "y": 0, "z": -2.153})[1])
        commands.extend(self._add_object("alma_floor_lamp",
                                         position={"x": 3.637, "y": 0, "z": 2.45})[1])
        commands.extend(self._add_object("duffle_bag",
                                         position={"x": 2.213, "y": 0, "z": -1.578},
                                         rotation={"x": 0.0, "y": 29.550001010645264, "z": 0.0})[1])

        # Add the containers.
        self.container_0, container_commands_0 = self._add_container(model_name="shoebox_fused",
                                                                     contents=["sphere", "sphere"],
                                                                     position={"x": 0.779, "y": 0.3711542, "z": -0.546},
                                                                     rotation={"x": 0, "y": 13, "z": 0})
        commands.extend(container_commands_0)
        self.container_1, container_commands_1 = self._add_container(model_name="shoebox_fused",
                                                                     contents=["cone", "cone", "cone", "cone"],
                                                                     position={"x": 1.922, "y": 0.3359459, "z": 1.25},
                                                                     rotation={"x": 0, "y": 15, "z": 0})
        commands.extend(container_commands_1)

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

    def _init_avatar(self) -> None:
        self._create_avatar(avatar_id=self.avatar_id,
                            rotation=-15,
                            position={"x": 1.385, "y": 0, "z": -0.95})

        # Add a 3rd-person camera.
        cam_id = "c"
        self.add_overhead_camera(position={"x": 2.315, "y": 1.6, "z": -0.474},
                                 target_object=self.avatar_id,
                                 images="cam",
                                 cam_id=cam_id)
        self.communicate({"$type": "set_field_of_view",
                          "field_of_view": 60.0,
                          "avatar_id": cam_id})


if __name__ == "__main__":
    c = BoxRoomContainers(demo=True)
    # Initialize the scene. Add the objects, avatar, set global values, etc.
    c.init_scene()

    # Pick up each container, shake it, and put it down.
    for container, arm in zip([c.container_0, c.container_1], [Arm.left, Arm.right]):
        c.go_to(target=container, move_stopping_threshold=0.7, turn_force=700)
        c.grasp_object(object_id=container, arm=arm)
        c.shake(joint_name=f"elbow_{arm.name}")
        c.drop(do_motion=False)
    # Pick up the first container again.
    c.go_to(target=c.container_0, move_stopping_threshold=0.7)
    c.turn_to(target=c.container_0)
    c.grasp_object(object_id=c.container_0, arm=Arm.left, stop_on_mitten_collision=False)

    # Put the container on the sofa.
    c.go_to(target={"x": 1.721, "y": 0, "z": -1.847}, turn_stopping_threshold=2, move_stopping_threshold=0.2)
    c.turn_to(target={"x": 2.024, "y": 0.46, "z": -2.399})
    c.reach_for_target(arm=Arm.left, target={"x": 0, "y": 0.4, "z": 1}, do_motion=False)
    for i in range(20):
        c.communicate([])
    c.drop()
    c.end()
