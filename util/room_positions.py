import numpy as np
from tdw.controller import Controller
from sticky_mitten_avatar.util import ROOM_MAP_DIRECTORY, OCCUPANCY_MAP_DIRECTORY, OCCUPANCY_CELL_SIZE
from sticky_mitten_avatar.environments import Environments


class RoomPositions(Controller):
    """
    Determine which positions of each floorplan are inside each room.
    """

    def get_positions(self) -> None:
        """
        Load each floorplan. Get environments data.
        Load an occupancy map and map its positions to the rooms (environments) in the scene.
        Write the results to disk.
        """

        spawn_positions = dict()
        # Iterate through each floorplan scene.
        for scene in [1, 2, 4, 5]:
            spawn_positions[scene] = dict()

            # Load the scene and get environment data.
            resp = self.communicate([self.get_add_scene(scene_name=f"floorplan_{scene}a"),
                                     {"$type": "send_environments"}])
            envs = Environments(resp=resp)

            # Load an occupancy map.
            occ = np.load(str(OCCUPANCY_MAP_DIRECTORY.joinpath(f"{scene}_0.npy").resolve()))
            rooms = np.full(occ.shape, -1, dtype=int)
            for ix, iy in np.ndindex(occ.shape):
                # Ignore positions outside of the scene.
                if occ[ix, iy] == 2:
                    continue
                # Get the room that this position is in.
                for i, env in enumerate(envs.envs):
                    x = envs.x_min + (ix * OCCUPANCY_CELL_SIZE)
                    z = envs.z_min + (iy * OCCUPANCY_CELL_SIZE)
                    if env.is_inside(x, z):
                        rooms[ix, iy] = i
                        break
            np.save(str(ROOM_MAP_DIRECTORY.joinpath(str(scene)).resolve()), np.array(rooms))
        self.communicate({"$type": "terminate"})


if __name__ == "__main__":
    RoomPositions().get_positions()
