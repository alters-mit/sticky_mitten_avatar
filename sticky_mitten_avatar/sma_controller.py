from typing import Dict, List, Union
from tdw.controller import Controller
from tdw.tdw_utils import TDWUtils
from sticky_mitten_avatar.avatar import Avatar
from sticky_mitten_avatar.entity import Entity


class StickyMittenAvatarController(Controller):
    def __init__(self, port: int = 1071, launch_build: bool = True, display: int = None,
                 avatar: str = "baby", position: Dict[str, float] = None, avatar_id: str = "a"):
        # Cache the entities.
        self._entities: List[Entity] = []
        super().__init__(port=port, launch_build=launch_build, display=display)

        self._initialize_scene()

        self.avatar = Avatar(c=self, avatar=avatar, position=position, avatar_id=avatar_id)
        self._entities.append(self.avatar)

    def _initialize_scene(self) -> None:
        """
        Initialize the scene. Override this to provide your own scene initialization.
        """

        self.start()
        self.communicate(TDWUtils.create_empty_room(30, 30))

    def communicate(self, commands: Union[dict, List[dict]]) -> list:
        # Send the commands and get a response.
        resp = super().communicate(commands)
        # Update the entities.
        for i in range(len(self._entities)):
            self._entities[i].on_frame(resp=resp)
        return resp
