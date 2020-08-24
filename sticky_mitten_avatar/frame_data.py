import numpy as np
from typing import List, Dict, Optional, Tuple
from tdw.output_data import OutputData, Rigidbodies, Images
from tdw.py_impact import PyImpact, AudioMaterial, Base64Sound


class FrameData:
    """
    Per-frame data that an avatar can use to decide what action to do next.

    Fields:

    - `audio` A list of tuples of audio generated by impacts. The first element in the tuple is a [`Base64Sound` object](https://github.com/threedworld-mit/tdw/blob/master/Documentation/python/py_impact.md#base64sound).
              The second element is the ID of the "target" (smaller) object.
              You can use the object ID to get the spatial position of the collision that created the audio.
    - `images` A dictionary of tuple of images mapped to the ID of the avatar that captured the image.
               The images tuple is (segmentation pass, depth pass). Either can be None.
    """

    _P = PyImpact()
    _STATIC_AUDIO_INFO = PyImpact.get_object_info()

    def __init__(self, resp: List[bytes], object_names: Dict[int, str], surface_material: AudioMaterial):
        """
        :param resp: The response from the build.
        :param object_names: The model name of key object. Key = the ID of the object in the scene.
        :param surface_material: The floor's [audio material](https://github.com/threedworld-mit/tdw/blob/master/Documentation/python/py_impact.md#audiomaterialenum).
        """

        self.audio: List[Tuple[Base64Sound, int]] = list()
        collisions, env_collisions, rigidbodies = FrameData._P.get_collisions(resp=resp)

        # Get the audio of each collision.
        for coll in collisions:
            if not FrameData._P.is_valid_collision(coll):
                continue
            # Determine which object has less mass.
            collider_id = coll.get_collider_id()
            collidee_id = coll.get_collidee_id()
            collider_info = FrameData._STATIC_AUDIO_INFO[object_names[collider_id]]
            collidee_info = FrameData._STATIC_AUDIO_INFO[object_names[collidee_id]]
            if collider_info.mass < collidee_info:
                target_id = collider_id
                target_amp = collider_info.amp
                target_mat = collider_info.material.name
                other_id = collidee_id
                other_amp = collidee_info.amp
                other_mat = collider_info.material.name
            else:
                target_id = collider_info
                target_amp = collider_info.amp
                target_mat = collider_info.material.name
                other_id = collider_info
                other_amp = collider_info.amp
                other_mat = collider_info.material.name
            audio = FrameData._P.get_sound(coll, rigidbodies, other_id, other_mat, target_id, target_mat,
                                           other_amp / target_amp)
            self.audio.append((audio, target_id))
        # Get the audio of each environment collision.
        for coll in env_collisions:
            collider_id = coll.get_object_id()
            if FrameData._get_velocity(rigidbodies, collider_id) > 0:
                collider_info = FrameData._STATIC_AUDIO_INFO[object_names[collider_id]]
                audio = FrameData._P.get_sound(coll, rigidbodies, 1, surface_material.name, collider_id,
                                               collider_info.material.name, 0.01 / collider_info.amp)
                self.audio.append((audio, collider_id))
        # Get the image data.
        self.images: Dict[str, Tuple[np.array, np.array]] = dict()
        for i in range(0, len(resp) - 1):
            if OutputData.get_data_type_id(resp[i]) == "imag":
                images = Images(resp[i])
                segmentation_pass: Optional[np.array] = None
                depth_pass: Optional[np.array] = None
                for j in range(images.get_num_passes()):
                    if images.get_pass_mask(j) == "_id":
                        segmentation_pass = images.get_image(j)
                    elif images.get_pass_mask(j) == "_depth":
                        depth_pass = images.get_image(j)
                self.images[images.get_avatar_id()] = (segmentation_pass, depth_pass)

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
