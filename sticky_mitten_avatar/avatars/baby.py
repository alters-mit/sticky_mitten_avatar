import numpy as np
from ikpy.chain import Chain
from ikpy.link import URDFLink
from sticky_mitten_avatar.avatars.avatar import Avatar


class Baby(Avatar):
    def _get_arm(self) -> Chain:
        return Chain(name="arm", links=[
            URDFLink(name="shoulder_pitch",
                     translation_vector=[0, 0, 0],
                     orientation=[-1.5708, 0, 0],
                     rotation=[1, 0, 0],
                     bounds=(-1.0472, 3.12414)),
            URDFLink(name="shoulder_yaw",
                     translation_vector=[0, -0.01, 0],
                     orientation=[-1.5708, 0, 0],
                     rotation=[0, -1, 0],
                     bounds=(-1.5708, 1.5708)),
            URDFLink(name="shoulder_roll",
                     translation_vector=[0, -0.01, 0],
                     orientation=[0, 0, 0],
                     rotation=[0, 0, 1],
                     bounds=(-0.785398, 0.785398)),
            URDFLink(name="elbow_pitch",
                     translation_vector=[0, -0.329993, 0],
                     orientation=[0, 0, 0],
                     rotation=[-1, 0, 0],
                     bounds=(0, 2.79253)),
            URDFLink(name="wrist_roll",
                     translation_vector=[0, -0.179993, 0],
                     orientation=[0, 0, 0],
                     rotation=[0, 0, -1],
                     bounds=(-1.5708, 1.5708)),
            URDFLink(name="wrist_pitch",
                     translation_vector=[0, -0.0625, 0],
                     orientation=[0, 0, 0],
                     rotation=[1, 0, 0],
                     bounds=(0, 1.5708))])

    def _get_mitten_offset(self) -> np.array:
        return np.array([0, -0.0625, 0])
