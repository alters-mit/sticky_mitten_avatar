from pathlib import Path
from json import dumps
from random import shuffle
from enum import Enum
import numpy as np
from typing import Tuple, Dict, Optional, List
from tdw.tdw_utils import TDWUtils
from tdw.output_data import OutputData, NavMeshPath
from sticky_mitten_avatar import StickyMittenAvatarController, Arm
from sticky_mitten_avatar.task_status import TaskStatus
from sticky_mitten_avatar.util import get_data


class _ActionType(Enum):
    """
    The type of action.
    """

    navigate = 1,
    grasp = 2,
    put_in_container = 4


class _ActionResult:
    """
    The result of a sequence of actions.
    """

    def __init__(self, success: bool, num_actions: int):
        """
        :param success: True if the task succeeded.
        :param num_actions: The number of actions in the task sequence.
        """

        self.success = success
        self.num_actions = num_actions


class NavTest(StickyMittenAvatarController):
    # Try to turn this many degrees per attempt at grasping an object.
    _D_THETA_GRASP = 15

    def __init__(self, port: int = 1071):
        super().__init__(port=port, launch_build=False, demo=False, id_pass=False, screen_width=256, screen_height=256,
                         debug=False)
        # Record the result of each action sequence.
        self.action_results: Dict[_ActionType, List[_ActionResult]] = dict()
        for t in _ActionType:
            self.action_results[t] = list()

    def _record_result(self, t: _ActionType, success: bool, num_actions: int) -> None:
        """
        Record the result of the action sequence.

        :param success: True if the action sequence was successful.
        :param t: The type of action.
        :param num_actions: The number of actions in the equence.
        """

        self.action_results[t].append(_ActionResult(success, num_actions))

    def _pop_last_action(self, t: _ActionType) -> Optional[_ActionResult]:
        """
        Pop the last action sequence.
        This is useful for recording overlapping action sequence results,
        e.g. a put-in-container action that requires grasp actions.

        :param t: The action type.

        :return: The last action result.
        """

        if len(self.action_results[t]) == 0:
            return None

        ar = self.action_results[t][-1]
        self.action_results[t] = self.action_results[t][:-1]
        return ar

    def _lift_arm(self, arm: Arm) -> None:
        """
        Lift the arm up.

        :param arm: The arm.
        """

        self.reach_for_target(arm=arm,
                              target={"x": -0.2 if arm == Arm.left else 0.2, "y": 0.4, "z": 0.3},
                              check_if_possible=False,
                              stop_on_mitten_collision=False)

    def get_navigable(self) -> Tuple[Dict[int, np.array], Dict[int, np.array]]:
        """
        :return: Tuple: Paths to all target objects; paths to all containers.
        """

        objects: Dict[int, np.array] = dict()
        containers: Dict[int, np.array] = dict()
        avatar_position = TDWUtils.array_to_vector3(self.frame.avatar_transform.position)
        commands = [{"$type": "set_floorplan_roof",
                     "show": False}]
        # Carve into the NavMesh.
        for object_id in self.static_object_info:
            # Skip target objects and containers.
            if self.static_object_info[object_id].target_object or self.static_object_info[object_id].container:
                continue
            commands.append({"$type": "make_nav_mesh_obstacle",
                             "id": object_id,
                             "carve_type": "stationary"})
        # Try to get a path to each object.
        for object_id in self.static_object_info:
            if self.static_object_info[object_id].target_object or self.static_object_info[object_id].container:
                object_position = TDWUtils.array_to_vector3(self.frame.object_transforms[object_id].position)
                # Ignore anything above the floor.
                if object_position["y"] < 0.03:
                    commands.append({"$type": "send_nav_mesh_path",
                                     "origin": avatar_position,
                                     "destination": object_position,
                                     "id": object_id})
        resp = self.communicate(commands)
        for i in range(len(resp) - 1):
            r_id = OutputData.get_data_type_id(resp[i])
            if r_id == "path":
                nav_mesh_path = NavMeshPath(resp[i])
                # If there is a valid path, add it to the dictionary.
                if nav_mesh_path.get_state() == "complete":
                    object_id = nav_mesh_path.get_id()
                    path = nav_mesh_path.get_path()
                    if self.static_object_info[object_id].target_object:
                        objects[object_id] = path
                    elif self.static_object_info[object_id].container:
                        containers[object_id] = path
                    else:
                        raise Exception(object_id)
        return objects, containers

    def navigate_to(self, object_id: int) -> bool:
        """
        Go to each waypoint on the path.

        :param object_id: The target object.

        :return: True if the avatar reached its destination.
        """

        num_actions = 0

        avatar_position = TDWUtils.array_to_vector3(self.frame.avatar_transform.position)
        object_position = TDWUtils.array_to_vector3(self.frame.object_transforms[object_id].position)
        resp = self.communicate({"$type": "send_nav_mesh_path",
                                 "origin": avatar_position,
                                 "destination": object_position,
                                 "id": object_id})
        nav_mesh_path = get_data(resp=resp, d_type=NavMeshPath)
        if nav_mesh_path.get_state() != "complete":
            return False

        # The first position in the path is always the origin.
        path = nav_mesh_path.get_path()[1:]

        for waypoint in path:
            # Lift any arms holding objects.
            for arm in [Arm.left, Arm.right]:
                self.reset_arm(arm=arm)
                self._lift_arm(arm)
                num_actions += 2

            self.communicate({"$type": "add_position_marker",
                              "position": TDWUtils.array_to_vector3(waypoint),
                              "scale": 0.3})
            num_tries = 0
            waypoint_status = self.go_to(target=TDWUtils.array_to_vector3(waypoint),
                                         stop_on_collision=False)
            num_actions += 1
            # The avatar might drift away from the target. Try again to go to it.
            while waypoint_status != TaskStatus.success and num_tries < 5:
                # Back up just a bit.
                self.turn_by(-179)
                self.move_forward_by(distance=0.5,
                                     move_stopping_threshold=0.3,
                                     num_attempts=10)
                # Try to go again.
                waypoint_status = self.go_to(target=TDWUtils.array_to_vector3(waypoint),
                                             stop_on_collision=False,
                                             move_stopping_threshold=0.3)
                num_actions += 3
                num_tries += 1
            if waypoint_status != TaskStatus.success:
                self._record_result(_ActionType.navigate, False, num_actions)
                print(f"Failed to go to {waypoint}")
                self.communicate({"$type": "remove_position_markers"})
                return False
        self._record_result(_ActionType.navigate, True, num_actions)
        print(f"Arrived at destination")
        self.communicate({"$type": "remove_position_markers"})
        return True

    def grasp_and_lift(self, object_id: int, arm: Optional[Arm] = None) -> bool:
        """
        Repeatedly try to grasp a nearby object. If the object was grasped, lift it up.

        :param object_id: The ID of the target object.
        :param arm: Set the arm that should grasp and lift.

        :return: Tuple: True if the avatar grasped the object; the number of actions the avatar did.
        """

        def _turn_to_grasp(direction: int, n: int) -> Tuple[bool, int]:
            theta = 0
            grasp_arm: Optional[Arm] = None
            # Try turning 45 degrees before giving up.
            # You can try adjusting this maximum.
            while theta < 45 and grasp_arm is None:
                # Try to grasp the object with each arm.
                for a in [Arm.left, Arm.right]:
                    if arm is not None and a != arm:
                        continue
                    s = self.grasp_object(object_id=object_id, arm=a)
                    n += 1
                    if s == TaskStatus.success:
                        grasp_arm = a
                        break
                    else:
                        self.reset_arm(arm=a)
                        n += 1
                if grasp_arm is None:
                    # Try turning some more.
                    s = self.turn_by(self._D_THETA_GRASP * direction)
                    n += 3
                    # Failed to turn.
                    if s != TaskStatus.success:
                        self._record_result(_ActionType.grasp, False, num_actions)
                        return False, n
                    theta += self._D_THETA_GRASP
            if grasp_arm is not None:
                self._lift_arm(arm=grasp_arm)
                n += 1
                self._record_result(_ActionType.grasp, True, n)
            return grasp_arm is not None, n

        num_actions = 0
        success, num_actions = _turn_to_grasp(1, num_actions)
        if success:
            print(f"Picked up {object_id}")
            return True

        # Reset the rotation.
        status = self.turn_by(-45)
        num_actions += 1
        if status != TaskStatus.success:
            self._record_result(_ActionType.grasp, False, num_actions)
            print(f"Failed to turn for some reason??")
            return False

        # Try turning the other way.
        success, num_actions = _turn_to_grasp(-1, num_actions)
        if success:
            print(f"Picked up {object_id}")
        else:
            print(f"Failed to pick up {object_id}")
        return success

    def is_holding_container(self) -> Tuple[bool, int]:
        """
        :return: Tuple: True if either mitten is holding a container; the ID of the container.
        """

        for arm in self.frame.held_objects:
            for object_id in self.frame.held_objects[arm]:
                if self.static_object_info[object_id].container:
                    return True, object_id
        return False, -1

    def put_in_container_sequence(self, object_id: int, container_id: int) -> bool:
        """
        A sequence of API calls to put an object in a container.

        :param object_id: The ID of the object.
        :param container_id: The ID of the container.

        :return: True if the avatar put the object in the container.
        """

        def _grasp(a: Arm, n: int, o: int) -> Tuple[bool, int]:
            """
            Grasp an object with the target arm and add the number of actions to my total.

            :param a: The arm.
            :param n: The number of actions for the put-in-container action sequence.
            :param o: The object ID.

            :return: True if the avatar grasped the object.
            """

            g = self.grasp_and_lift(object_id=o, arm=a)
            result = self._pop_last_action(t=_ActionType.grasp)
            n += result.num_actions
            if not g:
                # The container arm is the arm closest to the container.
                self._record_result(_ActionType.put_in_container, False, n)
            return g, n

        # Are we currently holding a container? If so, in what arm?
        container_arm: Optional[Arm] = None
        holding_container = False
        holding_object = False
        # Reset the arms.
        self.reset_arm(arm=Arm.left)
        self.reset_arm(arm=Arm.right)

        num_actions = 2
        for arm in [Arm.left, Arm.right]:
            # Are we already holding the container?
            for o_id in self.frame.held_objects[arm]:
                if o_id == container_id:
                    holding_container = True
                    container_arm = arm
                elif o_id == object_id:
                    holding_object = True
        # We are not holding the container. Get a free mitten.
        if container_arm is None:
            for arm in [Arm.left, Arm.right]:
                if len(self.frame.held_objects[arm]) == 0:
                    container_arm = arm
                    break
        # If both mittens are holding objects, drop everything and assign a container arm.
        if container_arm is None:
            print("Holding too many objects. Dropping everything.")
            # Drop everything.
            self.drop(arm=Arm.left)
            self.drop(arm=Arm.right)
            num_actions += 2
            container_arm = Arm.left
        # Pick up the object with the other arm.
        object_arm = Arm.left if container_arm is Arm.right else Arm.right

        # Pick up the container.
        if not holding_container:
            success, num_actions = _grasp(a=container_arm, n=num_actions, o=container_id)
            if not success:
                print("Failed to pick up container")
                return False
        else:
            print("Already holding container.")
        # Pick up the object.
        if not holding_object:
            success, num_actions = _grasp(a=object_arm, n=num_actions, o=object_id)
            if not success:
                print("Failed to pick up object")
                return False
        else:
            print("Already holding object.")

        # Reset the arms.
        self.reset_arm(arm=Arm.left)
        self.reset_arm(arm=Arm.right)

        lift_container_target = {"x": -0.2 if container_arm == Arm.left else 0.2, "y": 0.2, "z": 0.32}

        # Lift the container.
        self.reach_for_target(target=lift_container_target,
                              arm=container_arm,
                              check_if_possible=False,
                              stop_on_mitten_collision=False)
        # Put the object in the container.
        status = self.put_in_container(object_id=object_id, container_id=container_id, arm=object_arm)
        num_actions += 4

        # Pour out a full container.
        if status == TaskStatus.full_container:
            print("Container is full. Trying to pour out.")
            status = self.pour_out_container(arm=container_arm)
            num_actions += 1

            # If the pour action was successful, try again to put the object in the container.
            if status == TaskStatus.success:
                print("Poured out container.")
                status = self.put_in_container(object_id=object_id, container_id=container_id, arm=object_arm)
                print(f"Tried to put object in container: {status}")
                num_actions += 1
            else:
                print(f"Failed to pour out container: {status}")

        # Move the arms away and reset their positions.
        self.reach_for_target(target=lift_container_target, arm=Arm.left)
        self.reset_arm(arm=Arm.right)
        self.reset_arm(arm=Arm.left)

        num_actions += 3

        success = status != TaskStatus.success
        self._record_result(t=_ActionType.put_in_container, success=success, num_actions=num_actions)
        if success:
            print("The object is in the container")
        else:
            print("Failed to put the object is in the container")
        return success

    def run(self) -> None:
        """
        Run the test.
        Try to go to each target object and put it in the container.
        Record the success of each action and the number of sub-actions required.
        """

        self.init_scene(scene="2a", layout=1, room=1)
        # Get all objects and containers that the avatar can navigate to.
        target_object_paths, container_paths = self.get_navigable()
        container_ids = list(container_paths.keys())

        while len(container_ids) == 0:
            self.init_scene(scene="2a", layout=1, room=1)
            # Get all objects and containers that the avatar can navigate to.
            target_object_paths, container_paths = self.get_navigable()
            container_ids = list(container_paths.keys())

        for target_object_id in target_object_paths:
            # Go to the object.
            navigated = self.navigate_to(target_object_id)

            # Try to pick up the object.
            if navigated:
                grasped = self.grasp_and_lift(target_object_id)
                if grasped:
                    holding_container, container_id = self.is_holding_container()
                    # Go to a container.
                    if not holding_container:
                        shuffle(container_ids)
                        container_id = container_ids[0]
                        navigated = self.navigate_to(container_id)
                        if navigated:
                            self.put_in_container_sequence(container_id=container_id, object_id=target_object_id)
                    # Use a held container.
                    else:
                        self.put_in_container_sequence(container_id=container_id, object_id=target_object_id)
            self.write_results()

    def write_results(self) -> None:
        """
        Write the results of the test to disk as a json file.
        """

        results = dict()
        for t in self.action_results:
            num_successes = 0.0
            num_total = len(self.action_results[t])
            num_actions: List[float] = list()
            for a in self.action_results[t]:
                if a.success:
                    num_successes += 1
                    num_actions.append(a.num_actions)
            if num_total == 0:
                accuracy = 0
            else:
                accuracy = num_successes / num_total
            if len(num_actions) == 0:
                avg_num_actions = 0
            else:
                avg_num_actions = float(sum(num_actions)) / len(num_actions)
            results[t.name] = {"accuracy": accuracy,
                               "avg_num_actions": avg_num_actions}
        dump = dumps(results, indent=2, sort_keys=True)
        print(dump)
        Path("nav_test.json").write_text(dump)


if __name__ == "__main__":
    c = NavTest()
    try:
        c.run()
    finally:
        c.write_results()
        c.end()
