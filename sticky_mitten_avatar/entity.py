from typing import List
from abc import ABC, abstractmethod


class Entity(ABC):
    """
    An entity is something in the scene that should be updated per-frame.
    """

    @abstractmethod
    def on_frame(self, resp: List[bytes]) -> None:
        """
        Do something per frame.

        :param resp: The response from the build.
        """

        raise Exception("Not defined.")
