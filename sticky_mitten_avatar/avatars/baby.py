from typing import List
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
                     bounds=(0, 1.5708)),
            URDFLink(name="mitten",
                     translation_vector=[0, 0, -0.0625],
                     orientation=[0, 0, 0],
                     rotation=[0, 0, 0])])

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
                     bounds=(0, 1.5708)),
            URDFLink(name="mitten",
                     translation_vector=[0, 0, -0.0625],
                     orientation=[0, 0, 0],
                     rotation=[0, 0, 0])])

    def _get_default_sticky_mitten_profile(self) -> dict:
        return {"shoulder_pitch": {"mass": 3, "damper": 555, "force": 150, "angular_drag": 200},
                "shoulder_yaw": {"mass": 3, "damper": 555, "force": 150, "angular_drag": 200},
                "shoulder_roll": {"mass": 3, "damper": 555, "force": 150, "angular_drag": 200},
                "elbow": {"mass": 2, "damper": 555, "force": 150, "angular_drag": 200},
                "wrist_roll": {"mass": 1.5, "damper": 530, "force": 150, "angular_drag": 200},
                "wrist_pitch": {"mass": 1.5, "damper": 505, "force": 125, "angular_drag": 200}}

    def _get_start_bend_sticky_mitten_profile(self) -> dict:
        return {"shoulder_pitch": {"mass": 3, "damper": 75, "force": 450, "angular_drag": 1},
                "shoulder_yaw": {"mass": 3, "damper": 75, "force": 450, "angular_drag": 1},
                "shoulder_roll": {"mass": 3, "damper": 75, "force": 450, "angular_drag": 1},
                "elbow": {"mass": 2, "damper": 75, "force": 450, "angular_drag": 1},
                "wrist_roll": {"mass": 1.5, "damper": 500, "force": 450, "angular_drag": 1},
                "wrist_pitch": {"mass": 1.5, "damper": 50, "force": 345, "angular_drag": 1}}

    def _get_reset_arm_sticky_mitten_profile(self) -> dict:
        return {"shoulder_pitch": {"mass": 3, "damper": 0, "force": 250, "angular_drag": 10},
                "shoulder_yaw": {"mass": 3, "damper": 0, "force": 250, "angular_drag": 10},
                "shoulder_roll": {"mass": 3, "damper": 0, "force": 250, "angular_drag": 10},
                "elbow": {"mass": 2, "damper": 0, "force": 250, "angular_drag": 10},
                "wrist_roll": {"mass": 1.5, "damper": 0, "force": 250, "angular_drag": 10},
                "wrist_pitch": {"mass": 1.5, "damper": 0, "force": 225, "angular_drag": 10}}

    def _get_mass(self) -> float:
        return 80
