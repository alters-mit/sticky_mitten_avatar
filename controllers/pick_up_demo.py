from typing import Optional
from sticky_mitten_avatar import Arm
from sticky_mitten_avatar.task_status import TaskStatus
from sticky_mitten_avatar.demo_controller import DemoController


class PickUpDemo(DemoController):
    def __init__(self, port: int = 1071, launch_build: bool = True):
        super().__init__(port=port, launch_build=launch_build, output_directory="D:/pick_up_demo")

    def run(self) -> None:
        self.init_scene(scene="2c", layout=1, room=1, target_objects_room=1)
        self.communicate({"$type": "set_screen_size",
                          "width": 128,
                          "height": 128})
        container_id: Optional[int] = None
        for object_id in self.static_object_info:
            if self.static_object_info[object_id].container:
                container_id = object_id
                break
        assert container_id is not None, "No container in this scene. Re-run the controller."
        self.communicate({"$type": "teleport_object",
                          "id": container_id,
                          "position": {"x": -8.43, "y": 0, "z": -0.14}})
        self._wait_for_objects_to_stop([container_id])
        container_arm = Arm.left
        object_arm = Arm.right
        for i in range(4):
            picked_up = False
            num_attempts = 0
            object_id = self._target_object_ids[i]
            while not picked_up and num_attempts < 3:
                # Pick up the container.
                if container_id not in self.frame.held_objects[container_arm]:
                    self._go_to_and_lift(object_id=container_id, arm=container_arm, stopping_distance=0.4)
                # Pick up the object.
                if object_id not in self.frame.held_objects[object_arm]:
                    self._go_to_and_lift(object_id, arm=object_arm, stopping_distance=0.3)
                status = self.put_in_container(object_id=object_id, container_id=container_id, arm=object_arm)
                if status == TaskStatus.success:
                    picked_up = True
                num_attempts += 1
        self.end()


if __name__ == "__main__":
    PickUpDemo().run()
