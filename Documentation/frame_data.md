# FrameData

`from sticky_mitten_avatar.sticky_mitten_avatar.frame_data import FrameData`

Data about the scene from the most recent frame about doing an action such as `reach_for_target()`.
Use this data to plan what the next action should be.
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

# Prints all objects held by the left mitten.
print(c.frame.held_objects[Arm.left])
```

***

## Functions

***

#### \_\_init\_\_

**`def __init__(self, resp: List[bytes], avatar: Avatar)`**

| Parameter | Description |
| --- | --- |
| resp | The response from the build. |
| avatar | The avatar in the scene. |

#### save_images

**`def save_images(self, output_directory: Union[str, Path]) -> None`**

Save the ID pass (segmentation colors) and the depth pass to disk.
Images will be named: `[frame_number]_[pass_name].[extension]`
For example, the depth pass on the first frame will be named: `00000000_depth.png`
The image pass is a jpg file and the other passes are png files.

| Parameter | Description |
| --- | --- |
| output_directory | The directory that the images will be saved to. |

#### get_pil_images

**`def get_pil_images(self) -> dict`**

Convert each image pass to PIL images.

_Returns:_  A dictionary of PIL images. Key = the pass name (img, id, depth); Value = The PIL image (can be None)

#### get_depth_values

**`def get_depth_values(self) -> np.array`**

Convert the `depth_pass` to depth values.

_Returns:_  A decoded depth pass as a numpy array of floats.

