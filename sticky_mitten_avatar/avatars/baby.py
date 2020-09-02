import numpy as np
from ikpy.chain import Chain
from ikpy.link import URDFLink, OriginLink
from sticky_mitten_avatar.avatars.avatar import Avatar


class Baby(Avatar):
    """
    A small sticky mitten avatar.

    See API documentation for `Avatar`.
    """

    def _get_left_arm(self) -> Chain:
        return Chain(name="left_arm", links=[
            OriginLink(),
            URDFLink(name="shoulder_pitch",
                     translation_vector=[-0.225, 0.565, 0.075],
                     orientation=[-np.pi / 2, 0, 0],
                     rotation=[-1, 0, 0],
                     bounds=(-1.0472, 3.12414)),
            URDFLink(name="shoulder_yaw",
                     translation_vector=[0, 0, 0],
                     orientation=[0, 0, 0],
                     rotation=[0, 1, 0],
                     bounds=(-1.5708, 1.5708)),
            URDFLink(name="shoulder_roll",
                     translation_vector=[0, 0, 0],
                     orientation=[0, 0, 0],
                     rotation=[0, 0, 1],
                     bounds=(-0.785398, 0.785398)),
            URDFLink(name="elbow_pitch",
                     translation_vector=[0, 0, -0.235],
                     orientation=[0, 0, 0],
                     rotation=[-1, 0, 0],
                     bounds=(0, 2.79253)),
            URDFLink(name="wrist_roll",
                     translation_vector=[0, 0, -0.15],
                     orientation=[0, 0, 0],
                     rotation=[0, 0, 1],
                     bounds=(-1.5708, 1.5708)),
            URDFLink(name="wrist_pitch",
                     translation_vector=[0, 0, 0],
                     orientation=[0, 0, 0],
                     rotation=[-1, 0, 0],
                     bounds=(0, 1.5708))])

    def _get_right_arm(self) -> Chain:
        return Chain(name="right_arm", links=[
            OriginLink(),
            URDFLink(name="shoulder_pitch",
                     translation_vector=[0.235, 0.565, 0.075],
                     orientation=[-np.pi / 2, 0, 0],
                     rotation=[-1, 0, 0],
                     bounds=(-1.0472, 3.12414)),
            URDFLink(name="shoulder_yaw",
                     translation_vector=[0, 0, 0],
                     orientation=[0, 0, 0],
                     rotation=[0, 1, 0],
                     bounds=(-1.5708, 1.5708)),
            URDFLink(name="shoulder_roll",
                     translation_vector=[0, 0, 0],
                     orientation=[0, 0, 0],
                     rotation=[0, 0, 1],
                     bounds=(-0.785398, 0.785398)),
            URDFLink(name="elbow_pitch",
                     translation_vector=[0, 0, -0.235],
                     orientation=[0, 0, 0],
                     rotation=[-1, 0, 0],
                     bounds=(0, 2.79253)),
            URDFLink(name="wrist_roll",
                     translation_vector=[0, 0, -0.15],
                     orientation=[0, 0, 0],
                     rotation=[0, 0, 1],
                     bounds=(-1.5708, 1.5708)),
            URDFLink(name="wrist_pitch",
                     translation_vector=[0, 0, 0],
                     orientation=[0, 0, 0],
                     rotation=[-1, 0, 0],
                     bounds=(0, 1.5708))])
