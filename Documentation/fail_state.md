# Fail States in the API

**It is possible for any avatar API call to "fail"** at its task. What the cause of failure is, and what the fail state is, varies between API calls. These fail states are necessary because the Sticky Mitten Avatar is 100% physics-driven and there will always be situations in which:

- The solution to an API call is ***unsolvable*** meaning that it's not possible to determine an "optimal" or even "possible" solution with a general-purpose algorithm. However, an agent equipped with ML data can be trained to do any of these tasks successfully.
- The solution to an API call is ***impossible***, meaning that no solution exists.

## Arm API

### [`go_to()`](sma_controller.md#go_toself-target-uniondictstr-float-int-turn_force-float--1000-turn_stopping_threshold-float--015-move_force-float--80-move_stopping_threshold-float--035-avatar_id-str--a---bool) and [`move_forward_by`](sma_controller.md#move_forward_byself-distance-float-move_force-float--80-move_stopping_threshold-float--035-avatar_id-str--a---bool)

#### **Unnavigable**

**There is no built-in pathfinding/navigation solution in this API.** The avatar will always try to move in a straight line to a target. If the avatar isn't facing the target, it will first turn to face it.

Navigation is ***unsolvable*** because:

- There is no single "correct" pathfinding solution.
- The target might be unreachable.

Consider the following example:
![](images/navigation.png)

- You can use the API as-is to attempt *Option A*. This can't be considered to be a "bad" option because the avatar might actually arrive at the target by knocking the table out of the way.
- *Option B* and *Option C* are equally "good" in the context of a typical pathfinding algorithm. For research purposes, it may be insufficient to arbitrarily choose one instead of the other.
- *Option D* might be contextually the best option, even though it is the slowest. The avatar might want to go to an intermediate position, or avoid getting too close to the table, etc.

#### How to handle these fail states

Both `go_to()` and `move_forward_by()` return a boolean; if `True`, the movement was successful. If `False`, the movement failed, and the avatar has stopped moving.

By default, the Sticky Mitten Avatar API has the following fail states for ***impossible*** situations:

- The avatar collided with the environment (such as a wall) or a large object (mass >= 90)
- The avatar moved past the target.

To develop a navigation plan for an avatar, use [FrameData](frame_data.md) and [the static data cached in the controller](sma_controller.md).

***

### [`turn_to()`](sma_controller.md#put_downself-reset_arms-bool--true-do_motion-bool--true-avatar_id-str--a---none) and [`turn_by()`](sma_controller.md#turn_byself-angle-float-force-float--1000-stopping_threshold-float--015-avatar_id-str--a---bool)

The avatar might slightly overshoot the target, in which case it will stop turning.

#### How to handle these fail states

Both `turn_to()` and `turn_by()` return a boolean: `True` if the turn motion was successful. If `False`, move the avatar to a new location and try again.

***

### [`bend_arm()`](sma_controller.md#bend_armself-arm-arm-target-dictstr-float-do_motion-bool--true-avatar_id-str--a---bool)

#### Unreachable

The avatar will fail to bend an arm to the target if the target is unreachable  (***impossible***), in which case the avatar won't bend its arms at all.

#### Physically impossible

The avatar might try to bend an arm to a target and fail. In this case, the motion continues until all arm joints stop moving. Reasons that the arm motion might fail include:

- The avatar is holding something heavy and might not be strong enough (***impossible***).
- There is an occluding object in the way (***unsolvable***) Consider the following scenario:
![](images/cant_pick_up.png)

In this scenario, the **target** is occluded behind a box. The avatar calculates the _IK (inverse kinematics) solution_ to for the mitten (hand) to reach the target (red arrow). However, the mitten will collide with the box (orange line). The arm might be able to hook around the box (pink arrow); however, this solution is a) impossible to solve for (because the occluder would need to be described in IK-space) and b) has many possible options.

#### How to handle these fail states

The `bend_arm()` function returns `True` if the action was successful. You can use this boolean, and the [frame data](https://github.com/alters-mit/sticky_mitten_avatar/blob/master/Documentation/frame_data.md) to reposition the avatar and try again.

***

### [`pick_up()`](sma_controller.md#pick_upself-object_id-int-do_motion-bool--true-avatar_id-str--a---bool-arm)

All of the fail states of `bend_arm()` apply to `pick_up()`. Additionally:

#### The object is too far away

See "**`go_to()` and `move_forward_by()`**", above. If the object isn't within immediate range of the avatar, it is considered unreachable and the arms won't bend (***unsolvable***).

#### The object can never be reached

An object can be positioned such that the avatar will never be able to reach it. (***impossible***):
![](images/big_table.png)

In this scenario, the table is too wide for the avatar to reach across.

#### How to handle these fail states

- See recommendations for `bend_arm()`.
- The function returns `(bool, Arm)` where the bool is whether or not the arm picked up the object; if it's `False`, reposition the avatar and try again.

***

### [`put_down()`](sma_controller.md#put_downself-reset_arms-bool--true-do_motion-bool--true-avatar_id-str--a---none)

If the avatar isn't holding any objects (***impossible***), it will still reset its limbs to a "neutral" position.

***

### [`shake()`](sma_controller.md#shakeself-joint_name-str--elbow_left-axis-str--pitch-angle-tuplefloat-float--20-30-num_shakes-tupleint-int--3-5-force-tuplefloat-float--900-1000-avatar_id-str--a----none)

- The avatar won't navigate to an object; see **`pick_up()`** under "The object is too far away".
- The avatar won't try to first pick up the object. If it isn't holding an object, it will shake the limb anyway.

#### How to handle these fail states

- See recommendations for `bend_arm()` and `pick_up()`.