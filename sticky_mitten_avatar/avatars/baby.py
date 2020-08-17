from sticky_mitten_avatar.avatars._avatar import _Avatar
from ikpy.chain import Chain
from ikpy.link import OriginLink, URDFLink


class Baby(_Avatar):
    def _get_avatar_type(self) -> str:
        return "A_StickyMitten_Baby"

    def _get_left_arm(self) -> Chain:
        return Chain(name="left_arm", links=[
            OriginLink(),
            URDFLink(name="shoulder_pitch",
                     translation_vector=[-0.235, 0.565, 0.075],
                     orientation=[-1.5708, 0, 0],
                     rotation=[-1, 0, 0],
                     bounds=(-1.0472, 3.12414)),
            URDFLink(name="shoulder_yaw",
                     translation_vector=[-0.235, 0.565, 0.075],
                     orientation=[-1.5708, 0, 0],
                     rotation=[0, 1, 0],
                     bounds=(-1.5708, 1.5708)),
            URDFLink(name="shoulder_roll",
                     translation_vector=[-0.235, 0.565, 0.075],
                     orientation=[-1.5708, 0, 0],
                     rotation=[0, 0, 1],
                     bounds=(-0.785398, 0.785398)),
            URDFLink(name="elbow_pitch",
                     translation_vector=[-0.235, 0.329993, 0.075],
                     orientation=[-1.5708, 0, 0],
                     rotation=[-1, 0, 0],
                     bounds=(0, 2.79253)),
            URDFLink(name="wrist_roll",
                     translation_vector=[-0.235, 0.179993, 0.075],
                     orientation=[-1.5708, 0, 0],
                     rotation=[0, 0, 1],
                     bounds=(-1.5708, 1.5708)),
            URDFLink(name="wrist_pitch",
                     translation_vector=[-0.235, 0.179993, 0.075],
                     orientation=[-1.5708, 0, 0],
                     rotation=[-1, 0, 0],
                     bounds=(0, 1.5708))])

    def _get_right_arm(self) -> Chain:
        return Chain(name="right_arm", links=[
            OriginLink(),
            URDFLink(name="shoulder_pitch",
                     translation_vector=[0.235, 0.565, 0.075],
                     orientation=[-1.5708, 0, 0],
                     rotation=[-1, 0, 0],
                     bounds=(-1.0472, 3.12414)),
            URDFLink(name="shoulder_yaw",
                     translation_vector=[0.235, 0.565, 0.075],
                     orientation=[-1.5708, 0, 0],
                     rotation=[0, 1, 0],
                     bounds=(-1.5708, 1.5708)),
            URDFLink(name="shoulder_roll",
                     translation_vector=[0.235, 0.565, 0.075],
                     orientation=[-1.5708, 0, 0],
                     rotation=[0, 0, 1],
                     bounds=(-0.785398, 0.785398)),
            URDFLink(name="elbow_pitch",
                     translation_vector=[0.235, 0.329993, 0.075],
                     orientation=[-1.5708, 0, 0],
                     rotation=[-1, 0, 0],
                     bounds=(0, 2.79253)),
            URDFLink(name="wrist_roll",
                     translation_vector=[0.235, 0.179993, 0.075],
                     orientation=[-1.5708, 0, 0],
                     rotation=[0, 0, 1],
                     bounds=(-1.5708, 1.5708)),
            URDFLink(name="wrist_pitch",
                     translation_vector=[0.235, 0.179993, 0.075],
                     orientation=[-1.5708, 0, 0],
                     rotation=[-1, 0, 0],
                     bounds=(0, 1.5708))])
