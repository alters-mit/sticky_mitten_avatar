from typing import List, Dict
from abc import ABC, abstractmethod
from sticky_mitten_avatar.sma_controller import StickyMittenAvatarController


class SceneRecipe(ABC):
    """
    A recipe for loading a scene.
    """

    def __init__(self, c: StickyMittenAvatarController):
        """
        :param c: The controller.
        """

        self.commands = []
        self.commands.extend(self._get_scene_commands(c=c))

    def create_avatar(self, avatar_id: str, c: StickyMittenAvatarController) -> None:
        """
        Tell the controller to create an avatar.

        :param avatar_id: The ID of the avatar.
        :param c: The controller.
        """

        c.create_avatar(avatar_id=avatar_id,
                        position=self._get_avatar_position(),
                        rotation=self._get_avatar_rotation())

    @abstractmethod
    def _get_scene_commands(self, c: StickyMittenAvatarController) -> List[dict]:
        """
        :param c: The controller.

        :return: Commands to initialize the scene without any proc-gen (i.e. objects that never change in the scene).
        """

        raise Exception()

    @abstractmethod
    def _get_avatar_position(self) -> Dict[str, float]:
        """
        :return: The initial position of the avatar.
        """

        raise Exception()

    @abstractmethod
    def _get_avatar_rotation(self) -> float:
        """
        :return: The initial rotation of the avatar.
        """

        raise Exception()
