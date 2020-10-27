from io import BytesIO
from PIL import Image
from pathlib import Path
import numpy as np
from typing import List, Dict, Optional, Tuple, Union
from tdw.controller import Controller
from tdw.output_data import OutputData, Rigidbodies, Images, Transforms, CameraMatrices
from tdw.py_impact import AudioMaterial, Base64Sound
from tdw.tdw_utils import TDWUtils
from sticky_mitten_avatar.avatars.avatar import Avatar
from sticky_mitten_avatar.util import get_data
from sticky_mitten_avatar.avatars import Arm
from sticky_mitten_avatar.transform import Transform


class FrameData:
    """
    Per-frame data that an avatar can use to decide what action to do next.

    Access this data from the [StickyMittenAvatarController](sma_controller.md):

    ```python
    from sticky_mitten_avatar import StickyMittenAvatarController, Arm

    c = StickyMittenAvatarController()
    c.init_scene()

    # Look towards the left arm.
    c.rotate_camera_by(pitch=70, yaw=-45)

    c.reach_for_target(target={"x": -0.2, "y": 0.21, "z": 0.385}, arm=Arm.left)

    # Save the image.
    c.frame.save_images(output_directory="dist")
    c.end()
    ```

    ***

    ## Fields

    ### Visual

    - `image_pass` Rendered image of the scene as a numpy array.

     ![](images/pass_masks/img_0.jpg)

    - `id_pass` Image pass of object color segmentation as a numpy array. If `id_pass == False` in the `StickyMittenAvatarController` constructor, this will be None.

     ![](images/pass_masks/id_0.png)

    - `depth_pass` Image pass of depth values per pixel as a numpy array. Use the camera matrices to interpret this data.
       Depth values are encoded into the RGB image; see `get_depth_values()`.

     ![](images/pass_masks/depth_0.png)

    - `projection_matrix` The [camera projection matrix](https://github.com/threedworld-mit/tdw/blob/master/Documentation/api/output_data.md#cameramatrices) of the avatar's camera as a numpy array.
    - `camera_matrix` The [camera matrix](https://github.com/threedworld-mit/tdw/blob/master/Documentation/api/output_data.md#cameramatrices) of the avatar's camera as a numpy array.

    ### Objects

    - `object_transforms` The dictionary of object [transform data](transform.md). Key = the object ID.

    ```python
    for object_id in c.frame.object_transforms:
        print(c.frame.object_transforms[object_id].position)
    ```

    ### Avatar

    - `avatar_transform` The [transform data](transform.md) of the avatar.

    ```python
    avatar_position = c.frame.avatar_transform.position
    ```

    - `avatar_body_part_transforms` The [transform data](transform.md) of each body part of the avatar. Key = body part ID.

    ```python
    # Get the position and segmentation color of each body part.
    for body_part_id in c.frame.avatar_body_part_transforms:
        position = c.frame.avatar_body_part_transforms[body_part_id]
        segmentation_color = c.static_avatar_data[body_part_id]
    ```

    - `held_objects` A dictionary of IDs of objects held in each mitten. Key = arm:

    ```python
    from sticky_mitten_avatar import StickyMittenAvatarController, Arm

    c = StickyMittenAvatarController()

    # Your code here.

    # Prints all objects held by the left mitten at the last frame.
    print(c.frame.held_objects[Arm.left])
    ```

    ***

    ## Functions
    """

    def __init__(self, resp: List[bytes], avatar: Avatar):
        """
        :param resp: The response from the build.
        :param avatar: The avatar in the scene.
        """

        self._frame_count = Controller.get_frame(resp[-1])

        # Record avatar collisions.
        if avatar is not None:
            self.held_objects = {Arm.left: avatar.frame.get_held_left(),
                                 Arm.right: avatar.frame.get_held_right()}
        else:
            self.held_objects = None

        # Get the object transform data.
        self.object_transforms: Dict[int, Transform] = dict()
        tr = get_data(resp=resp, d_type=Transforms)
        for i in range(tr.get_num()):
            o_id = tr.get_id(i)
            self.object_transforms[o_id] = Transform(position=np.array(tr.get_position(i)),
                                                     rotation=np.array(tr.get_rotation(i)),
                                                     forward=np.array(tr.get_forward(i)))

        # Get camera matrix data.
        matrices = get_data(resp=resp, d_type=CameraMatrices)
        self.projection_matrix = matrices.get_projection_matrix()
        self.camera_matrix = matrices.get_camera_matrix()

        # Get the transform data of the avatar.
        self.avatar_transform = Transform(position=np.array(avatar.frame.get_position()),
                                          rotation=np.array(avatar.frame.get_rotation()),
                                          forward=np.array(avatar.frame.get_forward()))
        self.avatar_body_part_transforms: Dict[int, Transform] = dict()
        for i in range(avatar.frame.get_num_body_parts()):
            self.avatar_body_part_transforms[avatar.frame.get_body_part_id(i)] = Transform(
                position=np.array(avatar.frame.get_body_part_position(i)),
                rotation=np.array(avatar.frame.get_body_part_rotation(i)),
                forward=np.array(avatar.frame.get_body_part_forward(i)))

        # Get the image data.
        self.id_pass: Optional[np.array] = None
        self.depth_pass: Optional[np.array] = None
        self.image_pass: Optional[np.array] = None
        for i in range(0, len(resp) - 1):
            if OutputData.get_data_type_id(resp[i]) == "imag":
                images = Images(resp[i])
                for j in range(images.get_num_passes()):
                    if images.get_pass_mask(j) == "_id":
                        self.id_pass = images.get_image(j)
                    elif images.get_pass_mask(j) == "_depth" or images.get_pass_mask(j) == "_depth_simple":
                        self.depth_pass = images.get_image(j)
                    elif images.get_pass_mask(j) == "_img":
                        self.image_pass = images.get_image(j)

    def save_images(self, output_directory: Union[str, Path]) -> None:
        """
        Save the ID pass (segmentation colors) and the depth pass to disk.
        Images will be named: `[frame_number]_[pass_name].[extension]`
        For example, the depth pass on the first frame will be named: `00000000_depth.png`
        The image pass is a jpg file and the other passes are png files.

        :param output_directory: The directory that the images will be saved to.
        """

        if isinstance(output_directory, str):
            output_directory = Path(output_directory)
        if not output_directory.exists():
            output_directory.mkdir(parents=True)
        prefix = TDWUtils.zero_padding(self._frame_count, 8)
        # Save each image.
        for image, pass_name, ext in zip([self.image_pass, self.id_pass, self.depth_pass], ["img", "id", "depth"],
                                         ["jpg", "png", "png"]):
            if image is None:
                continue
            p = output_directory.joinpath(f"{prefix}_{pass_name}.{ext}")
            with p.open("wb") as f:
                f.write(image)

    def get_pil_images(self) -> dict:
        """
        Convert each image pass to PIL images.

        :return: A dictionary of PIL images. Key = the name of the pass (img, id, depth)
        """

        print(type(Image.open(BytesIO(self.image_pass))))

        return {"img": Image.open(BytesIO(self.image_pass)),
                "id": Image.open(BytesIO(self.id_pass)),
                "depth": Image.open(BytesIO(self.depth_pass))}

    def get_depth_values(self) -> np.array:
        """
        :return: A decoded depth pass as a numpy array of floats.
        """

        return TDWUtils.get_depth_values(self.depth_pass)

    @staticmethod
    def _get_velocity(rigidbodies: Rigidbodies, o_id: int) -> float:
        """
        :param rigidbodies: The rigidbody data.
        :param o_id: The ID of the object.

        :return: The velocity magnitude of the object.
        """

        for i in range(rigidbodies.get_num()):
            if rigidbodies.get_id(i) == o_id:
                return np.linalg.norm(rigidbodies.get_velocity(i))
