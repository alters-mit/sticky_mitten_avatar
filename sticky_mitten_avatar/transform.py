import numpy as np


class Transform:
    """
    Transform data for an object, avatar, body part, etc.

    ```python
    from sticky_mitten_avatar import StickyMittenAvatarController

    c = StickyMittenAvatarController()
    c.init_scene()

    # Print the position of the avatar.
    print(c.frame.avatar_transform.position)
    c.end()
    ```

    ***

    ## Fields

    - `position` The position of the object as a numpy array: `[x, y, z]` The position of each object is the bottom-center point of the object. The position of each avatar body part is in the exact center of the body part. `y` is the up direction.
    - `rotation` The rotation (quaternion) of the object as a numpy array: `[x, y, z, w]` See: [`tdw.tdw_utils.QuaternionUtils`](https://github.com/threedworld-mit/tdw/blob/master/Documentation/python/tdw_utils.md#quaternionutils).
    - `forward` The forward directional vector of the object as a numpy array: `[x, y, z]`

    ***

    ## Functions

    """

    def __init__(self, position: np.array, rotation: np.array, forward: np.array):
        """
        :param position: The position of the object as a numpy array.
        :param rotation: The rotation (quaternion) of the object as a numpy array.
        :param forward: The forward directional vector of the object as a numpy array.
        """

        self.position = position
        self.rotation = rotation
        self.forward = forward
