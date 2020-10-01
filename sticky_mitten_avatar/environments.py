from typing import List
from tdw.output_data import Environments as Envs
from sticky_mitten_avatar.util import get_data


class Environment:
    """
    Data for a single environment (i.e. a room) in a scene.
    """

    def __init__(self, env: Envs, i: int):
        """
        :param env: The environments output data.
        :param i: The index of this environment in env.get_num()
        """

        center = env.get_center(i)
        bounds = env.get_bounds(i)
        self.x_0 = center[0] - (bounds[0] / 2)
        self.z_0 = center[2] - (bounds[2] / 2)
        self.x_1 = center[0] + (bounds[0] / 2)
        self.z_1 = center[2] + (bounds[2] / 2)

    def is_inside(self, x: float, z: float) -> bool:
        """
        :param x: The x coordinate.
        :param z: The z coordinate.

        :return: True if position (x, z) is in the environment.
        """

        return self.x_0 <= x <= self.x_1 and self.z_0 <= z <= self.z_1


class Environments:
    """
    Data for each environment in the scene.
    An environment is an empty space in the scene, i.e. a room.

    ***

    ## Fields:

    - `x_min`: Minimum x position for all environments.
    - `x_max`: Maximum x position for all environments.
    - `z_min`: Minimum z position for all environments.
    - `z_max`: Maximum z position for all environments.
    - `enz`: Data for each environment in the scene.

    ***

    ## Functions:
    """

    def __init__(self, resp: List[bytes]):
        """
        :param resp: The response from the build.
        """

        env = get_data(resp=resp, d_type=Envs)

        # Get the overall size of the scene.
        self.x_min = 1000
        self.x_max = 0
        self.z_min = 1000
        self.z_max = 0
        self.envs: List[Environment] = list()
        for i in range(env.get_num()):
            e = Environment(env=env, i=i)
            if e.x_0 < self.x_min:
                self.x_min = e.x_0
            if e.z_0 < self.z_min:
                self.z_min = e.z_0
            if e.x_1 > self.x_max:
                self.x_max = e.x_1
            if e.z_1 > self.z_max:
                self.z_max = e.z_1
            self.envs.append(e)
