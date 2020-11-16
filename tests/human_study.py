from typing import List
from tdw.output_data import Keyboard
from sticky_mitten_avatar import StickyMittenAvatarController
from sticky_mitten_avatar.util import get_data


class HumanStudy(StickyMittenAvatarController):
    def __init__(self, port: int = 1071, screen_width: int = 256, screen_height: int = 256):
        super().__init__(port=port, launch_build=False, id_pass=False,
                         screen_width=screen_width, screen_height=screen_height)
        self.num_actions = 0
        self.done = False

    def _get_scene_init_commands(self, scene: str = None, layout: int = None, room: int = -1) -> List[dict]:
        commands = super()._get_scene_init_commands(scene=scene, layout=layout, room=room)
        commands.extend([{"$type": "send_keyboard", "frequency": "always"},
                         {"$type": "set_floorplan_roof", "show": False}])
        return commands

    def run(self) -> None:
        self.init_scene()
        while not self.done:
            resp = self.communicate([])
            keyboard = get_data(resp=resp, d_type=Keyboard)
            if keyboard is not None:
                for i in range(keyboard.get_num_pressed()):
                    if keyboard.get_pressed(i) == "RightArrow":
                        self.turn_right()
                    elif keyboard.get_pressed(i) == "LeftArrow":
                        self.turn_left()
                    elif keyboard.get_pressed(i) == "UpArrow":
                        self.move()

    def turn(self, angle: float) -> None:
        self.turn_by(angle)
        self.end_action()

    def turn_left(self) -> None:
        self.turn(-15)

    def turn_right(self) -> None:
        self.turn(15)

    def move(self) -> None:
        self.move_forward_by(0.8)
        self.end_action()

    def end_action(self) -> None:
        self.num_actions += 1
        if self.get_challenge_status():
            print(f"Number of actions to transport 1 object: {self.num_actions}")
            print(f"Estimated number of actions to transport all objects: "
                  f"{self.num_actions * (len(self._target_object_ids) + 2)}")
            self.end()

    def end(self) -> None:
        super().end()
        self.done = True


if __name__ == "__main__":
    c = HumanStudy()
    c.run()
