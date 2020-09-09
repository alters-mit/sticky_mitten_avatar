from typing import List
from sticky_mitten_avatar.test_controller import TestController


class Tap(TestController):
    def __init__(self, port: int = 1071, launch_build: bool = True, audio_playback_mode: str = None):
        super().__init__(port=port, launch_build=launch_build, audio_playback_mode=audio_playback_mode)
        self.object_id = 0

    def _get_scene_init_commands_early(self) -> List[dict]:
        commands = super()._get_scene_init_commands_early()
        commands.extend(self._add_object("coffee_table_glass_round",
                                         position={"x": 0, "y": 0, "z": 1},
                                         rotation={"x": 0, "y": 0, "z": 0},
                                         object_id=self.object_id))
        return commands


if __name__ == "__main__":
    c = Tap(launch_build=False)
    c.init_scene()
    c.go_to(target=c.object_id)
