from pathlib import Path
from typing import Dict, List, Union, Optional, Tuple
from tdw.tdw_utils import TDWUtils
from tdw.output_data import Images, CameraMatrices, OutputData
from sticky_mitten_avatar.avatars import Arm
from sticky_mitten_avatar import StickyMittenAvatarController
from sticky_mitten_avatar.util import get_data
from queue import Queue
import numpy as np
import pyastar
import time
import cv2
import math
import pickle
from sticky_mitten_avatar.task_status import TaskStatus
from sticky_mitten_avatar.paths import SURFACE_OBJECT_CATEGORIES_PATH
import argparse

import random

DISTANCE = 0.5
ANGLE = 15.
ANGLE1 = 60.
SCALE = 4
from json import loads
# ANGLE2 = 45.

import os

EXPLORED_POLICY = 0

DEMO = True


# 0: move forward
# 1: turn left
# 2: turn right
# 3: go_to
# 4: grasp
# 5: put_in_container
# 6: drop
# 7: lift_arm

class Nav(StickyMittenAvatarController):
    """
    1. map
    2. global goal
    3.
    """

    def __init__(self, port: int = 1071, launch_build: bool = False, demo=False, train=1):
        """
        :param port: The port number.
        :param launch_build: If True, automatically launch the build.
        """

        super().__init__(port=port, launch_build=launch_build, \
                         id_pass=True, demo=DEMO, train=train, screen_width=1024, screen_height=1024)
        self.demo = demo
        self.max_steps = 600
        self.map_id = 0
        self.surface_object_categories = \
            loads(SURFACE_OBJECT_CATEGORIES_PATH.read_text(encoding="utf-8"))
        self.output_directory = "D:/nav_images"
        self.image_count = 0

    def check_occupied(self, x: float, z: float):
        """
        Check (x, z) if occupied or free or out-side
        0: occupied; 1: free; 2: out_side
        """

        if self.occupancy_map is None or self._scene_bounds is None:
            return False, 0, 0, 0
        i = int(round((x - self._scene_bounds["x_min"]) * SCALE))
        j = int(round((z - self._scene_bounds["z_min"]) * SCALE))
        i = min(i, self.gt_map.shape[0] - 1)
        i = max(i, 0)
        j = min(j, self.gt_map.shape[1] - 1)
        j = max(j, 0)
        '''try:
            t = self.occupancy_map[i][j]
        except:
            print('error:', i, j)'''
        return 0, i, j, 0

    '''def get_occupancy_position(self, i, j):
        """
        Converts the position (i, j) in the occupancy map to (x, z) coordinates.

        :param i: The i coordinate in the occupancy map.
        :param j: The j coordinate in the occupancy map.
        :return: Tuple: True if the position is in the occupancy map; x coordinate; z coordinate.
        """

        if self.occupancy_map is None or self._scene_bounds is None:
            return False, 0, 0,
        x = self._scene_bounds["x_min"] + (i / SCALE)
        z = self._scene_bounds["z_min"] + (j / SCALE)
        return x, z'''

    '''def generate_goal(self):
        while True:
            x, z = np.random.random_sample(), np.random.random_sample()
            x = (self._scene_bounds["x_max"] - self._scene_bounds["x_min"]) * \
                                                        x + self._scene_bounds["x_min"]
            z = (self._scene_bounds["z_max"] - self._scene_bounds["z_min"]) * \
                                                        z + self._scene_bounds["z_min"]
            rep = self.check_occupied(x, z)
            #sx, _, sz = self.frame.avatar_transform.position
            if rep[3] == 1:# and self.l2_distance((sx, sz), (x, z)) > 4:
                return x, z
        return None'''

    def conv2d(self, map, kernel=3):
        from scipy.signal import convolve2d
        conv = np.ones((kernel, kernel))
        return convolve2d(map, conv, mode='same', boundary='fill')

    def find_shortest_path(self, st, goal, map=None):
        if map is None:
            map = self.map
        # map: 0-free, 1-occupied
        st_x, _, st_z = st
        g_x, g_z = goal
        _, st_i, st_j, t = self.check_occupied(st_x, st_z)
        # assert t == 1
        _, g_i, g_j, t = self.check_occupied(g_x, g_z)
        # assert t == 1
        dist_map = np.ones_like(map, dtype=np.float32)
        super_map1 = self.conv2d(map, kernel=5)
        dist_map[super_map1 > 0] = 10
        super_map2 = self.conv2d(map)
        dist_map[super_map2 > 0] = 1000
        dist_map[map > 0] = 100000
        self.dist_map = dist_map
        # print('min dist:', dist_map.min())
        # print('max dist:', dist_map.max())
        # dist_map
        path = pyastar.astar_path(dist_map, (st_i, st_j),
                                  (g_i, g_j), allow_diagonal=False)
        return path

    def l2_distance(self, st, g):
        return ((st[0] - g[0]) ** 2 + (st[1] - g[1]) ** 2) ** 0.5

    def check_goal(self, thresold=1.0):
        x, _, z = self.frame.avatar_transform.position
        gx, gz = self.goal
        d = self.l2_distance((x, z), (gx, gz))
        return d < thresold

    def draw(self, traj, value):
        if not isinstance(value, np.ndarray):
            value = np.array(value)
        for dx in range(1):
            for dz in range(1):
                x = traj[0] + dx
                z = traj[1] + dz
                self.paint[x, z] = value

    def dep2map(self):
        # start = time.time()
        pre_map = np.zeros_like(self.map)
        local_known_map = np.zeros_like(self.map, np.int32)
        try:
            depth = self.frame.get_depth_values()
        except:
            return pre_map
        # camera info
        FOV = 54.43222897365458
        W, H = depth.shape
        cx = W / 2.
        cy = H / 2.
        fx = cx / np.tan(math.radians(FOV / 2.))
        fy = cy / np.tan(math.radians(FOV / 2.))

        # Ego
        x_index = np.linspace(0, W - 1, W)
        y_index = np.linspace(0, H - 1, H)
        xx, yy = np.meshgrid(x_index, y_index)
        xx = (xx - cx) / fx * depth
        yy = (yy - cy) / fy * depth

        pc = np.stack((xx, yy, depth, np.ones((xx.shape[0], xx.shape[1]))))  # 3, 256, 256
        pc = pc.reshape(4, -1)

        E = self.frame.camera_matrix
        inv_E = np.linalg.inv(np.array(E).reshape((4, 4)))
        rot = np.array([[1, 0, 0, 0],
                        [0, -1, 0, 0],
                        [0, 0, -1, 0],
                        [0, 0, 0, 1]])
        inv_E = np.dot(inv_E, rot)

        rpc = np.dot(inv_E, pc).reshape(4, W, H)
        # pre_map = np.zeros_like(self.map)
        # print('dep2pc time: ', time.time() - start)
        rpc = rpc.reshape(4, -1)
        X = np.rint((rpc[0, :] - self._scene_bounds["x_min"]) * SCALE)
        X = np.maximum(X, 0)
        X = np.minimum(X, self.map_shape[0] - 1)
        Z = np.rint((rpc[2, :] - self._scene_bounds["z_min"]) * SCALE)
        Z = np.maximum(Z, 0)
        Z = np.minimum(Z, self.map_shape[1] - 1)
        depth = depth.reshape(-1)
        index = np.where((depth < 99) & (rpc[1, :] > 0.15) & (rpc[1, :] < 1.3))
        XX = X[index]
        ZZ = Z[index]
        # print(X.dtype, X.shape)
        XX = XX.astype(np.int32)
        ZZ = ZZ.astype(np.int32)
        pre_map[XX, ZZ] = 1

        index = np.where((depth < 99) & (rpc[1, :] < 1.0))
        X = X[index]
        Z = Z[index]
        # print(X.dtype, X.shape)
        X = X.astype(np.int32)
        Z = Z.astype(np.int32)
        local_known_map[X, Z] = 1
        self.known_map = np.maximum(self.known_map, local_known_map)
        # print('dep2pc time: ', time.time() - start)
        return pre_map

    def get_object_position(self, object_id):
        return self.frame.object_transforms[object_id].position

    def get_object_list(self):
        # seg = self.frame.id_pass
        images = self.frame.get_pil_images()
        seg = np.array(images['id'], np.int32)
        # hash = TDWUtils.color_to_hashable(seg)
        # print(seg.shape)
        W, H, _ = seg.shape
        hash = np.zeros((W, H), np.int32)
        hash[:, :] = (seg[:, :, 0] << 16) + (seg[:, :, 1] << 8) + seg[:, :, 2]
        hash = hash.reshape(-1)
        print(hash)
        hash = np.unique(hash)
        # print(hash)
        hash = hash[np.where(hash != 0)]
        # object_id = self.segmentation_color_to_id[hash]
        from operator import itemgetter
        self.object_list = {0: [], 1: [], 2: []}
        # if hash[0].shape[0] == 0:
        if len(hash) == 0:
            return
        '''try:
            self.object_ids = itemgetter(*hash)(self.segmentation_color_to_id)
        except:'''
        self.object_ids = []
        for i in hash:
            if i in self.segmentation_color_to_id:
                self.object_ids.append(self.segmentation_color_to_id[i])
        self.object_ids = tuple(self.object_ids)
        # print(type(self.object_ids))
        # self.object_ids = list(self.object_ids)
        if not isinstance(self.object_ids, tuple):
            # print(type(self.object_ids), self.object_ids)
            # print(self.static_object_info[self.object_ids].model_name)
            self.object_ids = [self.object_ids]
        # print(self.object_id)

        for id in self.object_ids:
            if id not in self.static_object_info:
                print('not in static:', id)
                continue
            if id in self.finish or id in self.held:
                continue
            if self.static_object_info[id].target_object:

                x, y, z = self.frame.object_transforms[id].position
                _, i, j, _ = self.check_occupied(x, z)
                if self.explored_map[i, j] == 0:
                    self.explored_map[i, j] = 1
                    self.id_map[i, j] = id
                    if EXPLORED_POLICY > 0:
                        self.net_map[0, 2, i, j] = 1
                    self.object_list[0].append(id)
            elif self.static_object_info[id].container:
                x, y, z = self.frame.object_transforms[id].position
                _, i, j, _ = self.check_occupied(x, z)
                if self.explored_map[i, j] == 0:
                    self.explored_map[i, j] = 2
                    self.id_map[i, j] = id
                    if EXPLORED_POLICY > 0:
                        self.net_map[0, 3, i, j] = 1
                    self.object_list[1].append(id)
            name = self.static_object_info[id].model_name
            if name in self.surface_object_categories and \
                    self.surface_object_categories[name] == self.goal_object:
                x, y, z = self.frame.object_transforms[id].position
                _, i, j, _ = self.check_occupied(x, z)
                if self.explored_map[i, j] == 0:
                    self.explored_map[i, j] = 3
                    if EXPLORED_POLICY > 0:
                        self.net_map[0, 4, i, j] = 1
                    self.id_map[i, j] = id
                    self.object_list[2].append(id)

    def grasp(self, object_id, arm):
        object_id = int(object_id)
        self.turn_to(object_id)
        if arm == Arm.left:
            d_theta = 15
        else:
            d_theta = -15
        grasped = False
        theta = 0
        while theta < 90 and not grasped:
            # Try to grasp the object.
            self.step += 1
            start = time.time()
            status = self.grasp_object(object_id=object_id,
                                       arm=arm,
                                       check_if_possible=True,
                                       stop_on_mitten_collision=True)
            self.action_list.append([4,
                                     self.demo_object_to_id[object_id],
                                     arm == Arm.right])
            # print('grasp time:', time.time() - start)
            # print('grasp:', status)
            if status == TaskStatus.success and \
                    object_id in self.frame.held_objects[arm]:
                self._lift_arm(arm)
                grasped = True
                break
            # Turn a bit and try again.
            if not grasped:
                # self.turn_by(d_theta)
                self.turn_by(angle=d_theta, force=1000, num_attempts=25)
                self.step += 1
                if d_theta == 15:
                    self.action_list.append([2])
                else:
                    self.action_list.append([1])
                theta += abs(d_theta)
            # print('theta:', theta)
        return grasped

    def move_to(self, max_move_step=130, d=0.7):
        move_step = 0
        # self.traj = []
        # self.draw_Astar_map()
        # print(self.map_num)
        too_long_num = 0
        while not self.check_goal(d) and move_step < max_move_step:
            if self.step > self.max_steps:
                break
            step_time = time.time()
            self.step += 1
            move_step += 1
            self.position = self.frame.avatar_transform.position

            self.get_object_list()
            pre_map = self.dep2map()
            self.map = np.maximum(self.map, pre_map)

            # self.update_map()

            path = self.find_shortest_path(self.position, self.goal, self.gt_map)
            gi, gj = path[min(2, len(path) - 1)]
            x, z = self.get_occupancy_position(gi, gj)
            # assert T == True
            local_goal = [x, z]
            angle = TDWUtils.get_angle(forward=np.array(self.frame.avatar_transform.forward),
                                       origin=np.array(self.frame.avatar_transform.position),
                                       position=np.array([local_goal[0], 0, local_goal[1]]))
            # print('angle:', angle)
            action_time = time.time()
            if np.abs(angle) < ANGLE:
                px, py, pz = self.frame.avatar_transform.position
                status = self.move_forward_by(distance=DISTANCE,
                                              move_force=300,
                                              move_stopping_threshold=0.2,
                                              num_attempts=25)
                x, y, z = self.frame.avatar_transform.position
                _, i, j, _ = self.check_occupied(x, z)
                self.traj.append((i, j))
                action = 0
                self.action_list.append([0])
                if self.l2_distance((px, pz), (x, z)) < 0.1:
                    x, y, z = np.array(self._avatar.frame.get_position()) + (
                                np.array(self._avatar.frame.get_forward()) * 0.25)
                    _, i, j, _ = self.check_occupied(x, z)
                    self.gt_map[i, j] = 1
                # if status == TaskStatus.too_long or status == TaskStatus.collided_with_environment:
                #    x, y, z = np.array(self._avatar.frame.get_position()) + (np.array(self._avatar.frame.get_forward()) * 0.25)
                #    _, i, j, _ = self.check_occupied(x, z)
                #    self.gt_map[i, j] = 1
            elif angle > 0:
                status = self.turn_by(angle=-ANGLE, force=1000, num_attempts=25)
                action = 1
                self.action_list.append([1])
                if status == TaskStatus.too_long:
                    self.turn_by(angle=ANGLE, force=1000, num_attempts=25)
                    self.move_forward_by(distance=DISTANCE,
                                         move_force=300,
                                         move_stopping_threshold=0.2,
                                         num_attempts=25)
                    self.step += 2
                    move_step += 1
                    x, y, z = self.frame.avatar_transform.position
                    _, i, j, _ = self.check_occupied(x, z)
                    self.traj.append((i, j))
                    self.action_list.append([2])
                    self.action_list.append([0])
            else:
                status = self.turn_by(angle=ANGLE, force=1000, num_attempts=25)
                action = 2
                self.action_list.append([2])
                if status == TaskStatus.too_long:
                    self.turn_by(angle=-ANGLE, force=1000, num_attempts=25)
                    self.move_forward_by(distance=DISTANCE,
                                         move_force=300,
                                         move_stopping_threshold=0.2,
                                         num_attempts=25)
                    self.step += 2
                    move_step += 1
                    x, y, z = self.frame.avatar_transform.position
                    _, i, j, _ = self.check_occupied(x, z)
                    self.traj.append((i, j))
                    self.action_list.append([1])
                    self.action_list.append([0])
            # self.action_list.append(action)
            action_time = time.time() - action_time
            step_time = time.time() - step_time
            x, y, z = self.frame.avatar_transform.position
            self.f.write('step: {}, position: {}, action: {}, goal: {}\n'.format(
                self.step, \
                self.frame.avatar_transform.position, \
                action, \
                self.goal
            ))
            self.f.write('local_goal: {}, distance: {}, angle: {}, forward: {}\n'.format(
                local_goal, \
                self.l2_distance((x, z), self.goal), \
                angle, \
                self.frame.avatar_transform.forward
            ))
            self.f.write('status: {}, action time: {}, step time: {}\n'.format(
                status, action_time, step_time))

            self.f.flush()

        # self.draw_map()
        return self.check_goal(d)

    def my_put_in_container(self, object_id, container_id, arm):
        self.action_list.append([5,
                                 self.demo_object_to_id[object_id],
                                 self.demo_object_to_id[container_id],
                                 arm == Arm.right])
        # print('before position:', self.frame.object_transforms[object_id].position)
        try:
            self._start_task()
            self.drop(arm)
            position = {'x': float(20 + random.randint(0, 10)),
                        'y': float(0.),
                        'z': float(20 + random.randint(0, 10))}

            self.communicate([{"$type": "teleport_object",
                               "position": position,
                               "id": object_id,
                               "physics": True}])
            self._end_task()
        except:
            print('put_in_container Error')
        # print('after position:', self.frame.object_transforms[object_id].position)
        return True

    def interact(self, object_id):
        if object_id in self.finish:
            return
        print('begin interact:', self.sub_goal)
        object_id = int(object_id)
        # self.frame.save_images(self.output_dir + f'/self.sub_goal')
        # print('??')
        # print(self.static_object_info[object_id].model_name)
        # d = np.linalg.norm(self.frame.avatar_transform.position - self.frame.object_transforms[object_id].position)
        # self.step += d / 0.5
        if self.sub_goal == 2:
            lift_high = True
        else:
            lift_high = False
        holding_arms = []
        for a in self.frame.held_objects:
            if len(self.frame.held_objects[a]) > 0:
                holding_arms.append(a)
        for a in holding_arms:
            self._lift_arm(arm=a, lift_high=lift_high)
        # print('!!')
        Flag = False

        x, y, z = self.frame.object_transforms[object_id].position
        self.goal = (x, z)
        s = False
        if self.sub_goal == 2:
            s = self.move_to(d=1.0)
        else:
            s = self.move_to()
        x, y, z = self.frame.avatar_transform.position
        _, i, j, _ = self.check_occupied(x, z)
        self.traj.append((i, j))
        if not s:
            # print('move position:', self.frame.object_transforms[object_id].position)
            # print(self.static_object_info[object_id].model_name)
            d = np.linalg.norm(self.frame.avatar_transform.position - self.frame.object_transforms[object_id].position)
            print('d0:', d)
            return False

        d = np.linalg.norm(self.frame.avatar_transform.position - self.frame.object_transforms[object_id].position)
        # print('distance:', d)
        # print(object_id)
        # print(self.static_object_info[object_id].model_name)
        # self.turn_to(object_id)
        self.step += 1
        if self.sub_goal < 2:
            self.go_to(object_id, move_stopping_threshold=0.3)
            self.action_list.append([3,
                                     self.demo_object_to_id[object_id],
                                     0.3])
        else:
            self.go_to(object_id, move_stopping_threshold=1.2)
            self.action_list.append([3,
                                     self.demo_object_to_id[object_id],
                                     0.6])
        d = np.linalg.norm(self.frame.avatar_transform.position - self.frame.object_transforms[object_id].position)
        if d > 0.7 and self.sub_goal < 2:
            # print('d1:', d)
            return False
        for a in holding_arms:
            self._lift_arm(arm=a, lift_high=lift_high)
        # print('sub goal:', self.sub_goal)
        if self.sub_goal < 2:
            grasp_arms = []

            for a in self.frame.held_objects:
                if len(self.frame.held_objects[a]) == 0:
                    grasp_arms.append(a)
            Flag = False
            arm = None
            print('grasp arm:', len(grasp_arms))
            if len(grasp_arms) == 0:
                return False
            x, y, z = self.frame.object_transforms[object_id].position
            _, i, j, _ = self.check_occupied(x, z)
            if not self.grasp(object_id, grasp_arms[0]):
                return False
            arm = grasp_arms[0]
            print('grasp:', object_id)
            self.explored_map[i, j] = 0
            index = np.where(self.id_map == object_id)
            self.explored_map[index[0], index[1]] = 0
            '''for a in grasp_arms:
                Flag = self.grasp(object_id, a)
                if Flag:
                    arm = a
                    break'''
            if self.static_object_info[object_id].container:
                if EXPLORED_POLICY > 0:
                    self.net_map[0, 3, i, j] = 0
                self.content_container[object_id] = []
                for a in holding_arms:
                    for o in self.frame.held_objects[a]:
                        if not self.container_full(self.container_held):
                            if a == Arm.left:
                                ac = Arm.right
                            else:
                                ac = Arm.left
                            self.reset_arm(ac)
                            status = self.put_in_container(object_id = o,
                                                    container_id = object_id,
                                                    arm=a)
                            print('put_in_container:', status)
                            if status != TaskStatus.success:

                                print(self.grasp(object_id, ac))
                        self.content_container[object_id].append(o)
            if self.container_held is not None:
                # print('???')
                start = time.time()
                if not self.container_full(self.container_held):
                    if arm == Arm.left:
                        ac = Arm.right
                    else:
                        ac = Arm.left
                    self.reset_arm(ac)
                    status = self.put_in_container(object_id = object_id,
                                                container_id = self.container_held,
                                                arm=arm)
                    print('put_in_container:', status, time.time() - start)
                    if status != TaskStatus.success:
                        if arm == Arm.left:
                            ac = Arm.right
                        else:
                            ac = Arm.left
                        print(self.grasp(self.container_held, ac))
                    self.content_container[self.container_held].append(object_id)
            if self.static_object_info[object_id].target_object:
                if EXPLORED_POLICY > 0:
                    self.net_map[0, 2, i, j] = 0
                self.update_held(object_id)
        else:
            Flag = True
            self.held_objects = []
            self.held_objects.extend(self.frame.held_objects[Arm.left])
            self.held_objects.extend(self.frame.held_objects[Arm.right])
            for id in self.held_objects:
                if self.is_container(id):
                    self.finish[id] = 1
                    content = self.content_container[id]
                    # overlap_ids = self._get_objects_in_container(container_id=id)
                    for o in content:
                        self.finish[o] = 1
                        self.update_finish(o)
                    self.content_container[id] = []
                else:
                    self.finish[id] = 1
                    self.update_finish(id)
            for a in holding_arms:
                self.drop(a)
                self.action_list.append([6, a == Arm.right])
            self.container_held = None
        return Flag

    def nav(self, max_nav_step):
        action = 0
        nav_step = 0
        self.pre_action = -1
        # while not self.check_goal() and nav_step < max_nav_step:
        while nav_step < max_nav_step:
            if EXPLORED_POLICY != 1 and self.check_goal():
                break
            if self.step > self.max_steps:
                break
            step_time = time.time()
            self.step += 1
            nav_step += 1
            self.position = self.frame.avatar_transform.position

            self.get_object_list()
            pre_map = self.dep2map()
            self.map = np.maximum(self.map, pre_map)
            if EXPLORED_POLICY > 0:
                self.update_map()
            status = None
            if len(self.object_list[1]) > 0:
                if self.sub_goal < 2 and not self.container_held and \
                        self.target_object_held.sum() > 2:
                    # print('begin interact with container')
                    self.sub_goal = 1
                    goal = random.choice(self.object_list[1])
                    self.interact(goal)
                    return

            if len(self.object_list[self.sub_goal]) > 0:
                # interact
                # print('begin interact')
                goal = random.choice(self.object_list[self.sub_goal])
                self.interact(goal)
                return
            action_time = time.time()
            if EXPLORED_POLICY != 1:
                path = self.find_shortest_path(self.position, self.goal, self.gt_map)
                i, j = path[min(2, len(path) - 1)]
                x, z = self.get_occupancy_position(i, j)
                # assert T == True
                local_goal = [x, z]
                angle = TDWUtils.get_angle(forward=np.array(self.frame.avatar_transform.forward),
                                           origin=np.array(self.frame.avatar_transform.position),
                                           position=np.array([local_goal[0], 0, local_goal[1]]))
                # print('angle:', angle)

                if np.abs(angle) < ANGLE:
                    px, py, pz = self.frame.avatar_transform.position
                    status = self.move_forward_by(distance=DISTANCE,
                                                  move_force=300,
                                                  move_stopping_threshold=0.2,
                                                  num_attempts=25)
                    x, y, z = self.frame.avatar_transform.position
                    _, i, j, _ = self.check_occupied(x, z)
                    self.traj.append((i, j))
                    self.action_list.append([0])
                    action = 0
                    if self.l2_distance((px, pz), (x, z)) < 0.1:
                        x, y, z = np.array(self._avatar.frame.get_position()) + (
                                    np.array(self._avatar.frame.get_forward()) * 0.25)
                        _, i, j, _ = self.check_occupied(x, z)
                        self.gt_map[i, j] = 1
                    # if status == TaskStatus.too_long or status == TaskStatus.collided_with_environment:
                    #    x, y, z = np.array(self._avatar.frame.get_position()) + (np.array(self._avatar.frame.get_forward()) * 0.25)
                    #    _, i, j, _ = self.check_occupied(x, z)
                    #    self.gt_map[i, j] = 1
                elif angle > 0:
                    status = self.turn_by(angle=-ANGLE, force=1000, num_attempts=25)
                    action = 1
                    self.action_list.append([1])
                    if status == TaskStatus.too_long:
                        self.turn_by(angle=ANGLE, force=1000, num_attempts=25)
                        self.move_forward_by(distance=DISTANCE,
                                             move_force=300,
                                             move_stopping_threshold=0.2,
                                             num_attempts=25)
                        self.step += 2
                        # nav_step += 1
                        x, y, z = self.frame.avatar_transform.position
                        _, i, j, _ = self.check_occupied(x, z)
                        self.traj.append((i, j))
                        self.action_list.append([2])
                        self.action_list.append([0])
                else:
                    status = self.turn_by(angle=ANGLE, force=1000, num_attempts=25)
                    action = 2
                    self.action_list.append([2])
                    if status == TaskStatus.too_long:
                        self.turn_by(angle=-ANGLE, force=1000, num_attempts=25)
                        self.move_forward_by(distance=DISTANCE,
                                             move_force=300,
                                             move_stopping_threshold=0.2,
                                             num_attempts=25)
                        self.step += 2
                        # nav_step += 1
                        x, y, z = self.frame.avatar_transform.position
                        _, i, j, _ = self.check_occupied(x, z)
                        self.traj.append((i, j))
                        self.action_list.append([1])
                        self.action_list.append([0])
            else:
                pass
                '''with torch.no_grad():
                    value, action, action_log_prob, self.recurrent_hidden_states = self.actor_critic.act(
                        self._obs(), self.recurrent_hidden_states,
                        self.masks, self.vector, deterministic=False)
                if action[0] == self.pre_action:
                    if random.random() < 0.3:
                        action[0] = random.randint(0, 2)

                if action[0] == 0:
                    status = self.move_forward_by(distance=DISTANCE,
                                        move_force = 300,
                                        move_stopping_threshold=0.2,
                                        num_attempts = 25)
                elif action[0] == 1:
                    status = self.turn_by(angle=-ANGLE, force=1000, num_attempts=25)
                elif action[0] == 2:
                    status = self.turn_by(angle=-ANGLE, force=1000, num_attempts=25)
                else:
                    assert False
                if status != TaskStatus.success:
                    self.pre_action = action[0]
                else:
                    self.pre_action = -1'''

            # self.action_list.append(action)
            action_time = time.time() - action_time
            step_time = time.time() - step_time
            x, y, z = self.frame.avatar_transform.position
            self.f.write('step: {}, position: {}, action: {}, goal: {}\n'.format(
                self.step, \
                self.frame.avatar_transform.position, \
                action, \
                0
            ))
            '''self.f.write('local_goal: {}, distance: {}, angle: {}, forward: {}\n'.format(
                    local_goal, \
                    self.l2_distance((x, z), self.goal), \
                    angle, \
                    self.frame.avatar_transform.forward
                ))'''
            self.f.write('status: {}, action time: {}, step time: {}\n'.format(
                status, action_time, step_time))

            self.f.flush()

    def _lift_arm(self, arm: Arm, lift_high=False) -> None:
        """
        Lift the arm up.

        :param arm: The arm.
        """
        return
        self.step += 1
        start = time.time()
        if lift_high:
            y = 0.6
        else:
            y = 0.4
        status = self.reach_for_target(arm=arm,
                                       target={"x": -0.2 if arm == Arm.left else 0.2, "y": y, "z": 0.3},
                                       check_if_possible=False,
                                       stop_on_mitten_collision=True)
        # print('lift time:', status, time.time() - start)

    def is_container(self, id):
        return self.static_object_info[id].container

    def container_full(self, container):
        '''start = time.time()
        overlap_ids = self._get_objects_in_container(container_id=container)
        end = time.time()
        if end - start > 0.1:
            print('full takes too much time')
        return len(overlap_ids) > 3'''
        return len(self.content_container[container]) > 3

    def decide_sub(self):
        self.held_objects = []
        self.held_objects.extend(self.frame.held_objects[Arm.left])
        self.held_objects.extend(self.frame.held_objects[Arm.right])
        if self.target_object_held.sum() == 0 or \
                (self.step > self.max_steps - 130 and len(self.held_objects) > 0):
            # all objects are found
            self.sub_goal = 2
        # elif self.step > self.max_steps - 50 and len(self.held_objects) > 0
        else:
            self.container_held = None
            if len(self.held_objects) > 0:
                for o in self.held_objects:
                    if self.is_container(o):
                        self.container_held = o
                        if self.container_full(o):
                            self.sub_goal = 2
                        else:
                            self.sub_goal = 0
                        return
            if self.container_held is None:
                # self.find_container_step < self.max_container_step and \
                if len(self.held_objects) >= 2:
                    self.sub_goal = 2
                if self.target_object_held.sum() > 2 and self.step < 700:
                    self.sub_goal = 1
                else:
                    self.sub_goal = 0

    def ex_goal(self):
        try_step = 0
        while try_step < 7:
            try_step += 1
            goal = np.where(self.known_map == 0)
            idx = random.randint(0, goal[0].shape[0] - 1)
            i, j = goal[0][idx], goal[1][idx]
            if self.map[i, j] == 0:
                self.goal = self.get_occupancy_position(i, j)
                return
        goal = np.where(self.known_map == 0)
        idx = random.randint(0, goal[0].shape[0] - 1)
        i, j = goal[0][idx], goal[1][idx]
        self.goal = self.get_occupancy_position(i, j)

    def update_finish(self, id):
        name = self.static_object_info[id].model_name
        print('final finish:', name)
        self.target_object_list[self.target_object_dict[name]] -= 1

    def update_held(self, id):
        self.held[id] = 1
        name = self.static_object_info[id].model_name
        print('held finish:', name)
        self.target_object_held[self.target_object_dict[name]] -= 1

    def run(self, scene='2a', layout=1, output_dir='transport', data_id=0) -> None:
        """
        Run a single trial. Save images per frame.
        """
        self.find_goal = 0
        self.find_object = 0
        self.find_container = 0
        if isinstance(output_dir, str):
            output_path = Path(output_dir)
        if not output_path.exists():
            output_path.mkdir(parents=True)

        self.output_dir = output_dir
        output_directory = output_dir
        start_time = time.time()
        self.init_scene(scene=scene, layout=layout, room=0, data_id=data_id)
        print('init scene time:', time.time() - start_time)

        if DEMO:
            self.communicate([{"$type": "set_floorplan_roof", "show": False}])
            self.add_overhead_camera({"x": 0.8, "y": 7.0, "z": -1.3},
                                     target_object="a",
                                     images="all")
            self._cam_commands.extend([{"$type": "send_images",
                                       "frequency": "once"}])
            # self.add_overhead_camera({"x": -5.5, "y": 8.0, "z": 1.0},
            #                            target_object="a",
            #                            images="avatars")
            # self._cam_commands.extend([{"$type": "send_images",
            #                            "frequency": "once"}])
            self._end_task()
        # return None
        # map: 0: free, 1: occupied
        # occupancy map: 0: occupied; 1: free; 2: out-side
        self.gt_map = np.zeros_like(self.occupancy_map)
        self.gt_map[self.occupancy_map != 1] = 1

        # self.construct_policy()
        # self.W = 128
        # self.H = 48
        if EXPLORED_POLICY == 0:
            # self.W = 200
            # self.H = 100
            self.W = self.occupancy_map.shape[0]
            self.H = self.occupancy_map.shape[1]
            x, y, z = self.frame.avatar_transform.position
            # self._scene_bounds["x_min"] = x - self.W / 2 / 4
            # self._scene_bounds["z_min"] = z - self.H / 2 / 4
            # self.map = np.zeros_like(self.occupancy_map)
            self.map = np.zeros((self.W, self.H))
            # 0: unknown, 1: known
            # self.known_map = np.zeros_like(self.occupancy_map, np.int32)
            self.known_map = np.zeros((self.W, self.H), np.int32)
            # 0: unknown, 1: target object, 2: container, 3: goal, 4: free
            # self.explored_map = np.zeros_like(self.occupancy_map, np.int32)
            self.explored_map = np.zeros((self.W, self.H), np.int32)
            # 0: unknown, 1: object_id(only target and container)
            # self.id_map = np.zeros_like(self.occupancy_map, np.int32)
            self.id_map = np.zeros((self.W, self.H), np.int32)
            # print('occupancy_map shape:', self.occupancy_map.shape)

            self.map_shape = (self.W, self.H)
        else:
            # self.map = np.zeros_like(self.occupancy_map)
            self.W = 128
            self.H = 48
            self.map = np.zeros((128, 48))
            self.known_map = np.zeros((128, 48), np.int32)
            self.explored_map = np.zeros((128, 48), np.int32)
            self.id_map = np.zeros((128, 48), np.int32)
        self.map_shape = (self.W, self.H)

        # self.construct_map()
        x, y, z = self.frame.avatar_transform.position
        self.position = self.frame.avatar_transform.position
        # print('init position:', x, y, z)
        # assert self.check_occupied(x, z)[3] == 1
        W, H = self.occupancy_map.shape

        self.step = 0
        self.map_num = 0
        action = 0

        self.goal_idx = []
        # self._target_object_ids: list
        self.container = []
        for i in self.static_object_info:
            if self.static_object_info[i].container:
                self.container.append(i)

        self.target_object_dict = {'vase_02': 0, 'jug04': 1, 'jug05': 2,
                                   'elephant_bowl': 0,
                                   'hexagonal_toy': 0}
        self.target_object_list = np.zeros(3, np.int32)
        self.target_object_held = np.zeros(3, np.int32)
        for i in self._target_object_ids:
            name = self.static_object_info[i].model_name
            # finish
            self.target_object_list[self.target_object_dict[name]] += 1
            # find but still held
            self.target_object_held[self.target_object_dict[name]] += 1
        self.total_target_object = self.target_object_list.sum()
        self.goal_dict = {'bed': 0,
                          'table': 1,
                          'coffee table': 2,
                          'sofa': 3,
                          'bench': 4}
        # self.goal_vec = np.zeros(5, np.int32)
        # self.goal_vec[self.goal_dict[self.goal_object]] += 1
        # self.goal_object = "coffee table"
        # self.goal_idx.append(random.choice(self._target_object_ids))
        # self.goal_idx.append(random.choice(self.container))
        print('goal object:', self.goal_object)
        self.finish = {}
        self.held = {}
        self.content_container = {}

        self.f = open(f'./{output_dir}/nav.log', 'w')
        ff = open(f'./{output_dir}/object.log', 'w')
        status = ''
        self.traj = []
        self.action_list = []
        self.step = 0
        # 0: find objects
        # 1: find container
        # 2: transport to goal
        # 3: Nav
        self.sub_goal = 1
        self.nav_goal = 0
        self.try_grasp = {}
        tot_start = time.time()
        while self.step < self.max_steps and self.target_object_list.sum() > 0:
            # make sure sub_goal
            # print(self.target_object_held.sum(), self.target_object_list.sum())
            self.decide_sub()

            goal = np.where(self.explored_map == self.sub_goal + 1)
            print('sub:', self.sub_goal, self.step, goal[0].shape[0])
            if goal[0].shape[0] > 0:
                # idx = random.randint(0, goal[0].shape[0] - 1)
                idx = 0
                i, j = goal[0][idx], goal[1][idx]
                self.goal = self.get_occupancy_position(i, j)
                # print(self.id_map[i, j])
                if self.id_map[i, j] in self.held:
                    self.explored_map[i, j] = 0
                    if EXPLORED_POLICY > 0:
                        self.net_map[2, i, j] = self.net_map[3, i, j] = 0
                    continue
                if self.sub_goal < 2:
                    if self.id_map[i, j] not in self.try_grasp:
                        self.try_grasp[self.id_map[i, j]] = 0
                    self.try_grasp[self.id_map[i, j]] += 1
                    if self.try_grasp[self.id_map[i, j]] >= 4:
                        self.try_grasp[self.id_map[i, j]] = 2
                        self.explored_map[i, j] = 0
                        self.id_map[i, j] = 0
                        continue
                self.interact(self.id_map[i, j])
                continue
            if EXPLORED_POLICY == 0:
                self.ex_goal()
                self.nav(120)
            elif EXPLORED_POLICY == 1:
                self.nav(60)
            else:
                # pass
                self.get_object_list()
                pre_map = self.dep2map()
                self.map = np.maximum(self.map, pre_map)
                self.update_map()
                self.high_policy()
                self.nav(60)
        # self.decide_sub()
        # print(self.held_objects)

        print('fianl time:', time.time() - tot_start)

        with open('action.pkl', 'wb') as fa:
            pickle.dump(self.action_list, fa)
        self.f.flush()
        ff.flush()
        # self.end()

    def communicate(self, commands: Union[dict, List[dict]]) -> List[bytes]:
        resp = super().communicate(commands=commands)
        any_images = False
        for j in range(len(resp) - 1):
            if OutputData.get_data_type_id(resp[j]) == "imag":
                any_images = True
                images = Images(resp[j])
                for k in range(images.get_num_passes()):
                    if images.get_pass_mask(k) == "_img":
                        fi = f"{self.image_count}.jpg"
                        output_dir = Path(self.output_directory).joinpath(images.get_avatar_id())
                        if not output_dir.exists():
                            output_dir.mkdir(parents=True)
                        with open(os.path.join(str(output_dir.resolve()), fi), "wb") as f:
                            f.write(images.get_image(k))

        if any_images:
            self.image_count += 1
        return resp


if __name__ == "__main__":
    port = 1071
    dd = 7
    c = Nav(port=port, launch_build=True, demo=True, train=2)
    fff = open(f'trans_ran_f{dd}.log', 'w', 10)
    try:
        total_grasp = 0
        total_finish = 0
        total = 0
        rate_grasp = 0
        rate_finish = 0
        # for i in range(dd * args.step, dd * args.step + args.step):

        # For variations of the simulation, change this value to 184, 43, 187, or 88
        i = 184

        print(i)
        c.run(output_dir=f'trans_ran_f{dd}', data_id=i)
        total_grasp += c.total_target_object - c.target_object_held.sum()
        total_finish += c.total_target_object - c.target_object_list.sum()
        total += c.total_target_object
        rate_grasp += 1 - c.target_object_held.sum() / c.total_target_object
        rate_finish += 1 - c.target_object_list.sum() / c.total_target_object
        print('epoch ', i)
        print('grasp:', c.total_target_object - c.target_object_held.sum())
        print('finish:', c.total_target_object - c.target_object_list.sum())
        print('total:', c.total_target_object)
        fff.write(f'epoch {i}:')
        fff.write(f'grasp: {c.total_target_object - c.target_object_held.sum()}')
        fff.write(f'finish: {c.total_target_object - c.target_object_list.sum()}')
        fff.write(f'total: {c.total_target_object}\n')
        fff.flush()
        # fff.write(f'{total_grasp}, {total_finish}, {rate_grasp}, {rate_finish}\n')
        # fff.write(f'{rate_grasp / 200}, {rate_finish / 200}')
        # print(total_grasp, total_finish, total, rate_grasp, rate_finish)
        # print(total_grasp / 200, total_finish / 200, total / 200, rate_grasp / 200, rate_finish / 200)
    finally:
        fff.close()