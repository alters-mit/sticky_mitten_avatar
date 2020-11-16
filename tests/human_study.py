from time import sleep
import keyboard
from sticky_mitten_avatar import StickyMittenAvatarController, Arm


class HumanStudy(StickyMittenAvatarController):
    def __init__(self, port: int = 1071, screen_width: int = 256, screen_height: int = 256):
        super().__init__(port=port, launch_build=False, id_pass=False,
                         screen_width=screen_width, screen_height=screen_height)
        self.key_down = False
        self.action_done = True
        self.num_actions = 0

        self.done = False

    def init_scene(self, scene: str = None, layout: int = None, room: int = -1) -> None:
        super().init_scene(scene=scene, layout=layout, room=room)
        keyboard.on_press_key("esc", lambda e: self.end())
        keyboard.on_press_key("left", lambda e: self.turn_left())
        keyboard.on_press_key("right", lambda e: self.turn_right())
        keyboard.on_press_key("up", lambda e: self.move())
        keyboard.on_release(callback=lambda e: self.set_ready())

    def reset_arms(self) -> None:
        self.reset_arm(Arm.left, precision=0.2, sub_action=True)
        self.reset_arm(Arm.right, precision=0.2, sub_action=True)

    def turn(self, angle: float) -> None:
        if not self.action_done or self.key_down:
            return
        self.key_down = True
        self.action_done = False
        self.reset_arms()
        self.turn_by(angle)
        self.end_action()
        self.action_done = True

    def turn_left(self) -> None:
        self.turn(-15)

    def turn_right(self) -> None:
        self.turn(15)

    def move(self) -> None:
        if not self.action_done or self.key_down:
            return
        self.key_down = True
        self.action_done = False
        self.reset_arms()
        self.move_forward_by(0.8)
        self.end_action()
        self.action_done = True

    def end_action(self) -> None:
        self.num_actions += 1
        if self.get_challenge_status():
            print(self.num_actions)
            self.end()

    def end(self) -> None:
        super().end()
        self.done = True

    def set_ready(self) -> None:
        self.key_down = False


if __name__ == "__main__":
    c = HumanStudy()
    c.init_scene()
    while not c.done:
        sleep(0.05)
