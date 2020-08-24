import random
from enum import Enum
import numpy as np
from typing import Dict, List, Union, Optional, Tuple
from tdw.controller import Controller
from tdw.tdw_utils import TDWUtils
from tdw.output_data import Bounds, Transforms, Rigidbodies
from sticky_mitten_avatar.avatars import Arm, Baby
from sticky_mitten_avatar.avatars.avatar import Avatar, Joint
from sticky_mitten_avatar.util import get_data, get_angle, get_closest_point_in_bounds
from sticky_mitten_avatar.physics_info import PhysicsInfo


class _TaskState(Enum):
    """
    The state of an avatar's motion.
    """

    ongoing = 1,
    success = 2,
    failure = 4


class StickyMittenAvatarController(Controller):
    """
    High-level API controller for sticky mitten avatars. Use this with the `Baby` and `Adult` avatar classes.
    This controller will cache static data for the avatars (such as segmentation colors) and automatically update
    dynamic data (such as position). The controller also has useful wrapper functions to handle the avatar API.

    ```python
    from tdw.tdw_utils import TDWUtils
    from sticky_mitten_avatar.avatars import Arm
    from sticky_mitten_avatar.sma_controller import StickyMittenAvatarController

    c = StickyMittenAvatarController(launch_build=False)

    # Create an empty room.
    c.start()
    c.communicate(TDWUtils.create_empty_room(12, 12))

    # Create an avatar.
    avatar_id = "a"
    c.create_avatar(avatar_id=avatar_id)

    # Bend an arm.
    c.bend_arm(avatar_id=avatar_id, target={"x": -0.2, "y": 0.21, "z": 0.385}, arm=Arm.left)
    ```

    ***

    Fields:

    - `on_resp` Default = None. Set this to a function with a `resp` argument to do something per-frame:

    ```python
    from sticky_mitten_avatar.sma_controller import StickyMittenAvatarController

    def _per_frame():
        print("This will happen every frame.")

    c = StickyMittenAvatarController(launch_build=False)
    c.on_resp = _per_frame
    ```
    """

    # A high drag value to stop movement.
    _STOP_DRAG = 1000

    def __init__(self, port: int = 1071, launch_build: bool = True):
        """
        :param port: The port number.
        :param launch_build: If True, automatically launch the build.
        """

        # Cache the entities.
        self._avatars: Dict[str, Avatar] = dict()
        # Commands sent by avatars.
        self._avatar_commands: List[dict] = []
        # Cached object physics info.
        self._objects: Dict[int, PhysicsInfo] = dict()

        # The command for the third-person camera, if any.
        self._cam_commands: Optional[list] = None
        # What to do after receiving a response.
        self.on_resp = None

        super().__init__(port=port, launch_build=launch_build)
        # Set image encoding to jpgs.
        self.communicate([{"$type": "set_img_pass_encoding",
                          "value": False}])

    def create_avatar(self, avatar_type: str = "baby", avatar_id: str = "a", position: Dict[str, float] = None,
                      debug: bool = False) -> None:
        """
        Create an avatar. Set default values for the avatar. Cache its static data (segmentation colors, etc.)

        :param avatar_type: The type of avatar. Options: "baby", "adult"
        :param avatar_id: The unique ID of the avatar.
        :param position: The initial position of the avatar.
        :param debug: If true, print debug messages when the avatar moves.
        """

        if avatar_type == "baby":
            avatar_type = "A_StickyMitten_Baby"
        elif avatar_type == "adult":
            avatar_type = "A_StickyMitten_Adult"
        else:
            raise Exception(f'Avatar type not found: {avatar_type}\nOptions: "baby", "adult"')

        if position is None:
            position = {"x": 0, "y": 0, "z": 0}

        commands = TDWUtils.create_avatar(avatar_type=avatar_type,
                                          avatar_id=avatar_id,
                                          position=position)[:]
        # Request segmentation colors, body part names, and dynamic avatar data.
        # Turn off the follow camera.
        # Set the palms to sticky.
        # Enable image capture.
        commands.extend([{"$type": "send_avatar_segmentation_colors",
                          "frequency": "once",
                          "ids": [avatar_id]},
                         {"$type": "send_avatars",
                          "frequency": "always"},
                         {"$type": "set_avatar_collision_detection_mode",
                          "mode": "continuous_dynamic",
                          "avatar_id": avatar_id},
                         {"$type": "set_avatar_drag",
                          "drag": self._STOP_DRAG,
                          "angular_drag": self._STOP_DRAG,
                          "avatar_id": avatar_id},
                         {"$type": "set_pass_masks",
                          "pass_masks": ["_img", "_id"],
                          "avatar_id": avatar_id},
                         {"$type": "send_images",
                          "frequency": "always"},
                         {"$type": "toggle_image_sensor",
                          "sensor_name": "FollowCamera",
                          "avatar_id": avatar_id},
                         {"$type": "send_rigidbodies",
                          "frequency": "always"},
                         {"$type": "send_transforms",
                          "frequency": "always"}])
        # Set all sides of both mittens to be sticky.
        for sub_mitten in ["palm", "back", "side"]:
            for is_left in [True, False]:
                commands.append({"$type": "set_stickiness",
                                 "sub_mitten": sub_mitten,
                                 "sticky": True,
                                 "is_left": is_left,
                                 "avatar_id": avatar_id,
                                 "show": False})
        # Strengthen the avatar.
        for joint in Avatar.JOINTS:
            commands.extend([{"$type": "adjust_joint_force_by",
                              "delta": 40,
                              "joint": joint.joint,
                              "axis": joint.axis,
                              "avatar_id": avatar_id},
                             {"$type": "adjust_joint_damper_by",
                              "delta": 300,
                              "joint": joint.joint,
                              "axis": joint.axis,
                              "avatar_id": avatar_id}])

        # Send the commands. Get a response.
        resp = self.communicate(commands)
        # Create the avatar.
        if avatar_type == "A_StickyMitten_Baby":
            avatar = Baby(avatar_id=avatar_id, debug=debug, resp=resp)
        else:
            raise Exception(f"Avatar not defined: {avatar_type}")
        # Cache the avatar.
        self._avatars[avatar_id] = avatar

    def communicate(self, commands: Union[dict, List[dict]]) -> List[bytes]:
        """
        Overrides `Controller.communicate()`.
        Before sending commands, append any automatically-added commands (such as arm-bending or arm-stopping).
        If there is a third-person camera, append commands to look at a target (see `add_overhead_camera()`).
        After sending the commands, update the avatar's `frame` data, and dynamic object data.
        Then, invoke `self.on_resp()` if it is not None.

        :param commands: Commands to send to the build.

        :return: The response from the build.
        """
        if not isinstance(commands, list):
            commands = [commands]
        # Add avatar commands from the previous frame.
        commands.extend(self._avatar_commands[:])

        # Append the third-party look-at command, if any.
        if self._cam_commands is not None:
            commands.extend(self._cam_commands)

        # Clear avatar commands.
        self._avatar_commands.clear()

        # Send the commands and get a response.
        resp = super().communicate(commands)

        if len(resp) == 1:
            return resp

        # Clear object info.
        self._objects.clear()
        # Update object info.
        tran = get_data(resp=resp, d_type=Transforms)
        rigi = get_data(resp=resp, d_type=Rigidbodies)

        if tran is None or rigi is None:
            return resp

        for i in range(tran.get_num()):
            o_id = tran.get_id(i)
            self._objects[o_id] = PhysicsInfo(o_id=o_id, rigi=rigi, tran=tran, tr_index=i)

        # Update the avatars. Add new avatar commands for the next frame.
        for a_id in self._avatars:
            self._avatar_commands.extend(self._avatars[a_id].on_frame(resp=resp))

        # Do something with the response per-frame.
        if self.on_resp is not None:
            self.on_resp(resp)

        return resp

    def get_add_object(self, model_name: str, object_id: int, position: Dict[str, float] = None,
                       rotation: Dict[str, float] = None, library: str = "", mass: int = 1,
                       scale: Dict[str, float] = None) -> List[dict]:
        """
        Overrides Controller.get_add_object; returns a list of commands instead of 1 command.

        :param model_name: The name of the model.
        :param position: The position of the model.
        :param rotation: The starting rotation of the model, in Euler angles.
        :param library: The path to the records file. If left empty, the default library will be selected.
                        See `ModelLibrarian.get_library_filenames()` and `ModelLibrarian.get_default_library()`.
        :param object_id: The ID of the new object.
        :param mass: The mass of the object.
        :param scale: The scale factor of the object. If None, the scale factor is (1, 1, 1)

        :return: A list of commands: `[add_object, set_mass, scale_object ,set_object_collision_detection_mode,
                                       send_transforms, send_rigidbodies]`
        """

        if position is None:
            position = {"x": 0, "y": 0, "z": 0}
        if rotation is None:
            rotation = {"x": 0, "y": 0, "z": 0}
        if scale is None:
            scale = {"x": 1, "y": 1, "z": 1}

        return [super().get_add_object(model_name=model_name, object_id=object_id, position=position,
                                       rotation=rotation, library=library),
                {"$type": "set_mass",
                 "mass": mass,
                 "id": object_id},
                {"$type": "scale_object",
                 "id": object_id,
                 "scale_factor": scale},
                {"$type": "set_object_collision_detection_mode",
                 "id": object_id,
                 "mode": "continuous_dynamic"},
                {"$type": "send_rigidbodies",
                 "frequency": "always"},
                {"$type": "send_transforms",
                 "frequency": "always"}]

    def bend_arm(self, avatar_id: str, arm: Arm, target: Dict[str, float], do_motion: bool = True) -> None:
        """
        Begin to bend an arm of an avatar in the scene. The motion will continue to update per `communicate()` step.

        :param arm: The arm (left or right).
        :param target: The target position for the mitten.
        :param avatar_id: The unique ID of the avatar.
        :param do_motion: If True, advance simulation frames until the pick-up motion is done. See: `do_joint_motion()`
        """

        self._avatar_commands.extend(self._avatars[avatar_id].bend_arm(arm=arm,
                                                                       target=TDWUtils.vector3_to_array(target)))

        if do_motion:
            self.do_joint_motion()

    def pick_up(self, avatar_id: str, object_id: int, do_motion: bool = True) -> Arm:
        """
        Begin to bend an avatar's arm to try to pick up an object in the scene.
        The simulation will advance 1 frame (to collect the object's bounds data).
        The motion will continue to update per `communicate()` step.

        :param object_id: The ID of the target object.
        :param avatar_id: The unique ID of the avatar.
        :param do_motion: If True, advance simulation frames until the pick-up motion is done. See: `do_joint_motion()`

        :return: The arm that is picking up the object.
        """

        # Get the bounds of the object.
        resp = self.communicate({"$type": "send_bounds",
                                 "frequency": "once",
                                 "ids": [object_id]})
        bounds = get_data(resp=resp, d_type=Bounds)
        commands, arm = self._avatars[avatar_id].pick_up(bounds=bounds, object_id=object_id)
        self._avatar_commands.extend(commands)

        if do_motion:
            self.do_joint_motion()
        return arm

    def put_down(self, avatar_id: str, reset_arms: bool = True) -> None:
        """
        Begin to put down all objects.
        The motion will continue to update per `communicate()` step.

        :param avatar_id: The unique ID of the avatar.
        :param reset_arms: If True, reset arm positions to "neutral".
        """

        self._avatar_commands.extend(self._avatars[avatar_id].put_down(reset_arms=reset_arms))

    def do_joint_motion(self) -> None:
        """
        Step through the simulation until the joints of all avatars are done moving.
        Useful when you want concurrent action (for example, multiple avatars in the same scene):

        ```python
        c = StickyMittenAvatarController()

        c.create_avatar(avatar_id="a")
        c.create_avatar(avatar_id="b")

        # Tell both avatars to start bending arms to different positions.
        # Set do_motion to False so that the avatars can act at the same time.
        c.bend_arm(avatar_id="a", target=pos_a, arm=Arm.left, do_motion=False)
        c.bend_arm(avatar_id="b", target=pos_b, arm=Arm.left, do_motion=False)

        # Wait until both avatars are done moving.
        self.do_joint_mothion()
        ```
        """

        done = False
        while not done:
            done = True
            # The loop is done if the IK goals are done.
            for avatar in self._avatars.values():
                if not avatar.is_ik_done():
                    done = False
            # Keep looping.
            if not done:
                self.communicate([])

    def stop_avatar(self, avatar_id: str) -> None:
        """
        Advance 1 frame and stop the avatar's movement and turning.

        :param avatar_id: The ID of the avatar.
        """

        self.communicate({"$type": "set_avatar_drag",
                          "drag": self._STOP_DRAG,
                          "angular_drag": self._STOP_DRAG,
                          "avatar_id": avatar_id})

    def turn_to(self, avatar_id: str, target: Union[Dict[str, float], int], force: float = 300,
                stopping_threshold: float = 0.1) -> bool:
        """
        The avatar will turn to face a target. This will advance through many simulation frames.

        :param avatar_id: The unique ID of the avatar.
        :param target: The target position or object ID.
        :param force: The force at which the avatar will turn. More force = faster, but might overshoot the target.
        :param stopping_threshold: Stop when the avatar is within this many degrees of the target.

        :return: True if the avatar succeeded in turning to face the target.
        """

        def get_turn_state() -> _TaskState:
            """
            :return: Whether avatar succeed, failed, or is presently turning.
            """

            angle = get_angle(origin=np.array(avatar.frame.get_position()),
                              forward=np.array(avatar.frame.get_forward()),
                              position=target)

            # Failure because the avatar turned all the way around without aligning with the target.
            if angle - initial_angle >= 360:
                return _TaskState.failure

            if angle > 180:
                angle -= 360

            # Success because the avatar is facing the target.
            if np.abs(angle) < stopping_threshold:
                return _TaskState.success

            return _TaskState.ongoing

        avatar = self._avatars[avatar_id]

        # Set the target if it wasn't already a numpy array (for example, if it's an object ID).
        target = self._get_position(target=target)

        # Get the initial angle to the target.
        initial_angle = get_angle(origin=np.array(avatar.frame.get_position()),
                                  forward=np.array(avatar.frame.get_forward()),
                                  position=np.array(target))
        # Decide which direction to turn.
        if initial_angle > 180:
            direction = -1
        else:
            direction = 1

        # Set a low drag.
        self.communicate({"$type": "set_avatar_drag",
                          "drag": 100,
                          "angular_drag": 0.05,
                          "avatar_id": avatar_id})

        turn_command = {"$type": "turn_avatar_by",
                        "torque": force * direction,
                        "avatar_id": avatar_id}

        # Begin to turn.
        self.communicate(turn_command)
        i = 0
        while i < 200:
            # Coast to a stop.
            coasting = True
            while coasting:
                coasting = np.linalg.norm(avatar.frame.get_angular_velocity()) > 0.05
                state = get_turn_state()
                if state == _TaskState.success:
                    self.stop_avatar(avatar_id=avatar_id)
                    return True
                elif state == _TaskState.failure:
                    self.stop_avatar(avatar_id=avatar_id)
                    return False
                self.communicate([])

            # Turn.
            self.communicate(turn_command)
            state = get_turn_state()
            if state == _TaskState.success:
                self.stop_avatar(avatar_id=avatar_id)
                return True
            elif state == _TaskState.failure:
                self.stop_avatar(avatar_id=avatar_id)
                return False
            i += 1
        self.stop_avatar(avatar_id=avatar_id)
        return False

    def go_to(self, avatar_id: str, target: Union[Dict[str, float], int],
              turn_force: float = 300, turn_stopping_threshold: float = 0.1,
              move_force: float = 80, move_stopping_threshold: float = 0.35) -> bool:
        """
        Go to a target position or object.
        If the avatar isn't facing the target, it will turn to face it (see `turn_to()`).

        :param avatar_id: The ID of the avatar.
        :param avatar_id: The unique ID of the avatar.
        :param target: The target position or object ID.
        :param turn_force: The force at which the avatar will turn. More force = faster, but might overshoot the target.
        :param turn_stopping_threshold: Stop when the avatar is within this many degrees of the target.
        :param move_force: The force at which the avatar will move. More force = faster, but might overshoot the target.
        :param move_stopping_threshold: Stop within this distance of the target.

        :return: True if the avatar arrived at the destination.
        """

        def get_state() -> _TaskState:
            """
            :return: Whether the avatar is at its destination, overshot it, or still going to it.
            """

            p = np.array(avatar.frame.get_position())
            d_from_initial = np.linalg.norm(initial_position - p)
            # Overshot. End.
            if d_from_initial > initial_distance:
                return _TaskState.failure
            # We're here! End.
            d = np.linalg.norm(p - target)
            if d <= move_stopping_threshold:
                return _TaskState.success
            # Keep truckin' along.
            return _TaskState.ongoing

        avatar = self._avatars[avatar_id]
        initial_position = avatar.frame.get_position()

        # Set the target. If it's an object, the target is the nearest point on the bounds.
        target = self._get_position(target=target, nearest_on_bounds=True, avatar_id=avatar_id)
        # Get the distance to the target.
        initial_distance = np.linalg.norm(np.array(initial_position) - target)

        # Turn to the target.
        self.turn_to(avatar_id=avatar_id, target=target, force=turn_force, stopping_threshold=turn_stopping_threshold)

        # Go to the target.
        self.communicate({"$type": "set_avatar_drag",
                          "drag": 0.1,
                          "angular_drag": 100,
                          "avatar_id": avatar_id})
        i = 0
        while i < 200:
            # Start gliding.
            self.communicate({"$type": "move_avatar_forward_by",
                              "magnitude": move_force,
                              "avatar_id": avatar_id})
            t = get_state()
            if t == _TaskState.success:
                self.stop_avatar(avatar_id=avatar_id)
                return True
            elif t == _TaskState.failure:
                self.stop_avatar(avatar_id=avatar_id)
                return False
            # Glide.
            while np.linalg.norm(avatar.frame.get_velocity()) > 0.1:
                self.communicate([])
                t = get_state()
                if t == _TaskState.success:
                    self.stop_avatar(avatar_id=avatar_id)
                    return True
                elif t == _TaskState.failure:
                    self.stop_avatar(avatar_id=avatar_id)
                    return False
            i += 1
        self.stop_avatar(avatar_id=avatar_id)
        return False

    def shake(self, avatar_id: str, joint_name: str = "elbow_left", axis: str = "pitch",
              angle: Tuple[float, float] = (20, 30), num_shakes: Tuple[int, int] = (6, 12),
              force: Tuple[float, float] = (400, 400)) -> None:
        """
        Shake a joint back and forth for multiple iterations.
        Per iteration, the joint will bend forward by an angle and then bend back by an angle.
        This will advance the simulation multiple frames.

        :param avatar_id: The ID of the avatar.
        :param joint_name: The name of the joint.
        :param axis: The axis of the joint's rotation.
        :param angle: Each shake will bend the joint by a angle in degrees within this range.
        :param num_shakes: The avatar will shake the joint a number of times within this range.
        :param force: The avatar will add strength to the joint by a value within this range.
        """

        # Check if the joint and axis are valid.
        joint: Optional[Joint] = None
        for j in Avatar.JOINTS:
            if j.joint == joint_name and j.axis == axis:
                joint = j
                break
        if joint is None:
            return

        force = random.uniform(force[0], force[1])
        damper = 200
        # Increase the force of the joint.
        self.communicate([{"$type": "adjust_joint_force_by",
                           "delta": force,
                           "joint": joint.joint,
                           "axis": joint.axis,
                           "avatar_id": avatar_id},
                          {"$type": "adjust_joint_damper_by",
                           "delta": -damper,
                           "joint": joint.joint,
                           "axis": joint.axis,
                           "avatar_id": avatar_id}])
        # Do each iteration.
        for i in range(random.randint(num_shakes[0], num_shakes[1])):
            a = random.uniform(angle[0], angle[1])
            # Start the shake.
            self.communicate({"$type": "bend_arm_joint_by",
                              "angle": a,
                              "joint": joint.joint,
                              "axis": joint.axis,
                              "avatar_id": avatar_id})
            for j in range(10):
                self.communicate([])
            # Bend the arm back.
            self.communicate({"$type": "bend_arm_joint_by",
                              "angle": -(a / 2),
                              "joint": joint.joint,
                              "axis": joint.axis,
                              "avatar_id": avatar_id})
            for j in range(10):
                self.communicate([])
            # Apply the motion.
            self.do_joint_motion()
        # Reset the force of the joint.
        self.communicate([{"$type": "adjust_joint_force_by",
                           "delta": -force,
                           "joint": joint.joint,
                           "axis": joint.axis,
                           "avatar_id": avatar_id},
                          {"$type": "adjust_joint_damper_by",
                           "delta": damper,
                           "joint": joint.joint,
                           "axis": joint.axis,
                           "avatar_id": avatar_id}])


    def add_overhead_camera(self, position: Dict[str, float], target_object: Union[str, int] = None, cam_id: str = "c",
                            images: str = "all") -> None:
        """
        Add an overhead third-person camera to the scene.
        Advances 1 frame.

        :param cam_id: The ID of the camera.
        :param target_object: Always point the camera at this object or avatar.
        :param position: The position of the camera.
        :param images: Image capture behavior. Choices:
                       1. `"cam"` (only this camera captures images)
                       2. `"all"` (avatars currently in the scene and this camera capture images)
                       3. `"avatars"` (only the avatars currently in the scene capture images)
        """

        commands = TDWUtils.create_avatar(avatar_type="A_Img_Caps_Kinematic",
                                          avatar_id=cam_id,
                                          position=position)
        if target_object is not None:
            # Get the avatar's object ID.
            if isinstance(target_object, str):
                self._cam_commands = [{"$type": "look_at_avatar",
                                       "target_avatar_id": target_object,
                                       "avatar_id": cam_id,
                                       "use_centroid": True},
                                      {"$type": "rotate_sensor_container_by",
                                       "axis": "pitch",
                                       "angle": -5,
                                       "avatar_id": cam_id}]
            else:
                self._cam_commands = [{"$type": "look_at",
                                       "object_id": target_object,
                                       "avatar_id": cam_id,
                                       "use_centroid": True}]
        if images != "avatars":
            commands.append({"$type": "set_pass_masks",
                             "pass_masks": ["_img"],
                             "avatar_id": cam_id})
        if images == "cam":
            # Disable avatar cameras.
            for avatar_id in self._avatars:
                commands.append({"$type": "toggle_image_sensor",
                                 "sensor_name": "SensorContainer",
                                 "avatar_id": avatar_id})
            commands.append({"$type": "send_images",
                             "ids": [cam_id],
                             "frequency": "always"})
        elif images == "all":
            commands.append({"$type": "send_images",
                             "frequency": "always"})
        self.communicate(commands)

    def _get_position(self, target: Union[Dict[str, float], np.array, int],
                      nearest_on_bounds: bool = False, avatar_id: str = None) -> np.array:
        """
        Convert the target to a numpy array. If the target is an object ID, get the object's position.

        :param target: The target position or object.
        :param avatar_id: The ID of the avatar. Used only if `nearest_on_bounds == True` and if `target` is an int.
        :param nearest_on_bounds: If True, `avatar_id is not None`, and `target` is an int, set the target position to
                                  the nearest point on the object bounds from the avatar's position.

        :return: The position.
        """

        # This is an object ID.
        if isinstance(target, int):
            if target not in self._objects:
                raise Exception(f"Object not found: {target}")
            # Get the nearest point from the avatar.
            if nearest_on_bounds and (avatar_id is not None):
                resp = self.communicate({"$type": "send_bounds",
                                         "ids": [target],
                                         "frequency": "once"})
                bounds = get_data(resp=resp, d_type=Bounds)
                return get_closest_point_in_bounds(bounds=bounds,
                                                   origin=self._avatars[avatar_id].frame.get_position(),
                                                   index=0)
            # Get the object's position.
            return self._objects[target].position
        elif isinstance(target, dict):
            return TDWUtils.vector3_to_array(target)
        else:
            return target
