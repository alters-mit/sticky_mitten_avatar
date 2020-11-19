from json import loads
from pathlib import Path
from typing import List, Dict
from tdw.tdw_utils import TDWUtils
from tdw.py_impact import ObjectInfo, AudioMaterial
from sticky_mitten_avatar import Arm
from sticky_mitten_avatar.util import CONTAINER_MASS, CONTAINER_SCALE, TARGET_OBJECT_MASS
from sticky_mitten_avatar.demo_controller import DemoController


class NavigationDemo(DemoController):
    """
    Demo controller for navigation and putting objects in containers.
    This is meant for generating a demo video. This is NOT a good example of an actual use-case.
    """

    def __init__(self, port: int = 1071, launch_build: bool = True):
        self.scene = "2c"
        self.layout = 1
        self.room = 1
        self._container_ids: List[int] = list()
        self._container_arm = Arm.right
        self._object_arm = Arm.left
        super().__init__(port=port, launch_build=launch_build, output_directory="D:/navigation_demo")

    def _get_scene_init_commands(self, scene: str = None, layout: int = None, room: int = -1,
                                 target_objects_room: int = -1) -> List[dict]:
        # Initialize the floorplan.
        # Note that this is NOT `_get_scene_init_commands()`.
        # This is a lower-level function that just loads the floorplan and is inherited from `FloorplanController`.
        # We are using this function because for this demo we want to explicitly place containers and target objects.
        commands = self.get_scene_init_commands(scene=self.scene, layout=self.layout, audio=True)

        target_object_scales = self._get_target_object_scales()

        # Load object placement data.
        object_and_container_data: Dict[str, List[dict]] = loads(Path("navigation_demo/objects.json").
                                                                 read_text(encoding="utf-8"))
        # Explicitly place the target objects.
        for obj in object_and_container_data["target_objects"]:
            target_object_audio = ObjectInfo(name=obj["name"], mass=TARGET_OBJECT_MASS, material=AudioMaterial.ceramic,
                                             resonance=0.6, amp=0.01, library="models_core.json", bounciness=0.5)
            scale = target_object_scales[obj["name"]]
            target_object_id, target_object_commands = self._add_object(model_name=obj["name"],
                                                                        position=obj["position"],
                                                                        rotation=obj["rotation"],
                                                                        library="models_core.json",
                                                                        scale={"x": scale, "y": scale, "z": scale},
                                                                        audio=target_object_audio)
            self._target_object_ids.append(target_object_id)
            commands.extend(target_object_commands)

        # Explicitly place the containers.
        for obj in object_and_container_data["containers"]:
            container_id, container_commands = self._add_object(model_name=obj["name"],
                                                                position=obj["position"],
                                                                rotation=obj["rotation"],
                                                                scale=CONTAINER_SCALE,
                                                                library="models_core.json",
                                                                audio=self._default_audio_values[obj["name"]])
            self._container_ids.append(container_id)
            commands.extend(container_commands)
            # Make the container much lighter.
            commands.append({"$type": "set_mass",
                             "id": container_id,
                             "mass": CONTAINER_MASS})
        # Initialize the avatar.
        commands.extend(self._get_avatar_init_commands(scene=self.scene, layout=self.layout, room=self.room))
        return commands

    def _put_object_in_container_by_index(self, object_index: int, container_index: int) -> None:
        """
        Put objects in containers using the indices in the object placement data arrays.

        :param object_index: The index (NOT the ID) of the target object.
        :param container_index: The index (NOT the ID) of the container.
        """

        self._lift_arm(arm=self._container_arm)
        self._go_to_and_lift(object_id=self._target_object_ids[object_index], stopping_distance=0.4,
                             arm=self._object_arm)
        if self._container_ids[container_index] not in self.frame.held_objects[self._container_arm]:
            self._go_to_and_lift(object_id=self._container_ids[container_index],
                                 arm=self._container_arm, stopping_distance=0.4)
        self.put_in_container(object_id=self._target_object_ids[object_index],
                              container_id=self._container_ids[container_index],
                              arm=self._object_arm)
        self.move_forward_by(-0.5)
        self._go_to_and_lift(object_id=self._container_ids[container_index],
                             arm=self._container_arm, stopping_distance=0.4)
        self.move_forward_by(-0.5)

    def run(self) -> None:
        """
        Go to different objects, put them in containers, and bring them to the goal zone.
        """

        self.init_scene()
        # Pick up the first container.
        self._go_to_and_lift(object_id=self._container_ids[0], arm=self._container_arm, stopping_distance=0.3)
        for index in [0, 1]:
            self._put_object_in_container_by_index(object_index=index, container_index=0)
        # Follow a path to the goal zone.
        for waypoint in [[-9.21, 0, 1.44], [-8.63, 0, 0.42], [0.3, 0, 0.42], [0.35, 0, -0.23]]:
            self.go_to(target=TDWUtils.array_to_vector3(waypoint), move_force=200)
        # Drop the container.
        self.drop(arm=self._container_arm)
        # Move back a bit.
        self.move_forward_by(-0.5)
        # Go to the next container.
        for waypoint in [[0.3, 0, 0.76], [-3.53, 0, 0.67]]:
            self.go_to(target=TDWUtils.array_to_vector3(waypoint))
        # Pick up the next container.
        self._go_to_and_lift(object_id=self._container_ids[1], arm=self._container_arm, stopping_distance=0.3)
        # Put the next object in the container.
        self._put_object_in_container_by_index(object_index=2, container_index=1)
        # Go to the last object.
        for waypoint in [[-4.48, 0, 0.32], [0.44, 0, 0.32], [0.44, 0, 2.32]]:
            self.go_to(target=TDWUtils.array_to_vector3(waypoint), move_force=200)
        # Pick up the last object.
        self._put_object_in_container_by_index(object_index=3, container_index=1)
        for waypoint in [[0.44, 0., 0.68], [-0.38, 0, -2.37]]:
            self.go_to(target=TDWUtils.array_to_vector3(waypoint), move_force=200)
        self.drop(arm=self._container_arm)
        self.reset_arm(arm=self._object_arm)
        self.move_forward_by(-0.8)
        # End the simulation.
        self.end()


if __name__ == "__main__":
    c = NavigationDemo(launch_build=False)
    c.run()
