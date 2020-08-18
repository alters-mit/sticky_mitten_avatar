from sticky_mitten_avatar.avatars.avatar import Avatar
from ikpy.chain import Chain
from ikpy.link import OriginLink, URDFLink


class Baby(Avatar):
    def _get_left_arm(self) -> Chain:
        return Chain(name="left_arm", links=[
            URDFLink(name="shoulder_pitch",
                     translation_vector=[0, 0, 0],
                     orientation=[-1.5708, 0, 0],
                     rotation=[1, 0, 0],
                     bounds=(-1.0472, 3.12414)),
            URDFLink(name="shoulder_yaw",
                     translation_vector=[0, 0, 0],
                     orientation=[0, 0, 0],
                     rotation=[0, -1, 0],
                     bounds=(-1.5708, 1.5708)),
            URDFLink(name="shoulder_roll",
                     translation_vector=[0, 0, 0],
                     orientation=[0, 0, 0],
                     rotation=[0, 0, -1],
                     bounds=(-0.785398, 0.785398)),
            URDFLink(name="elbow_pitch",
                     translation_vector=[0, -0.329993, 0],
                     orientation=[0, 0, 0],
                     rotation=[1, 0, 0],
                     bounds=(0, 2.79253)),
            URDFLink(name="wrist_roll",
                     translation_vector=[0, -0.179993, 0],
                     orientation=[0, 0, 0],
                     rotation=[0, 0, -1],
                     bounds=(-1.5708, 1.5708)),
            URDFLink(name="wrist_pitch",
                     translation_vector=[0, 0, 0],
                     orientation=[0, 0, 0],
                     rotation=[1, 0, 0],
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


if __name__ == "__main__":
    q = Chain(name="left_arm", links=[
            URDFLink(name="shoulder_pitch",
                     translation_vector=[0, 0, 0],
                     orientation=[-1.5708, 0, 0],
                     rotation=[1, 0, 0],
                     bounds=(-1.0472, 3.12414)),
            URDFLink(name="shoulder_yaw",
                     translation_vector=[0, 0, 0],
                     orientation=[0, 0, 0],
                     rotation=[0, -1, 0],
                     bounds=(-1.5708, 1.5708)),
            URDFLink(name="shoulder_roll",
                     translation_vector=[0, 0, 0],
                     orientation=[0, 0, 0],
                     rotation=[0, 0, -1],
                     bounds=(-0.785398, 0.785398)),
            URDFLink(name="elbow_pitch",
                     translation_vector=[0, -0.329993, 0],
                     orientation=[0, 0, 0],
                     rotation=[1, 0, 0],
                     bounds=(0, 2.79253)),
            URDFLink(name="wrist_roll",
                     translation_vector=[0, -0.179993, 0],
                     orientation=[0, 0, 0],
                     rotation=[0, 0, 1],
                     bounds=(-1.5708, 1.5708)),
            URDFLink(name="wrist_pitch",
                     translation_vector=[0, 0, 0],
                     orientation=[0, 0, 0],
                     rotation=[-1, 0, 0],
                     bounds=(0, 1.5708))
    ])
    import matplotlib.pyplot
    import ikpy.utils.plot as plot_utils
    fig, ax = plot_utils.init_3d_figure()
    target = [-0.4, 0.4, 0.271]
    rots = q.inverse_kinematics(target_position=target)

    q.plot(rots, ax, target=target)
    matplotlib.pyplot.show()