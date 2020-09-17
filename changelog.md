# Changelog

## 0.3.3

### Frontend

- `StickyMittenAvatarController`:
  - Replaced `audio_playback_mode` parameter in the constructor with `demo` (a boolean).
  - Removed `roll` parameter from `rotate_camera_by()`.
- `FrameData`:
  - Added fields: `camera_projection_matrix` and `camera_matrix`
  - Replaced field `positions` with `object_transforms` which includes rotations and forwards in addition to positions.
  - Added field: `avatar_transform` Avatar transform data.
  - Added field: `avatar_body_part_transforms` Transform data for each of the avatar's body parts.
- `StaticObjectInfo`:
  - Removed fields: `volume` and `hollowness`
- Added: `Transform` Transform data for an object, avatar, body part, etc.

### Backend

- `StickyMittenAvatarController`:
  - Fixed: Avatar can't pick up sub-objects of composite objects.
  - Fixed: No audio data for sub-objects of composite objects.
- Added utility script: `composite_object_audio.py` Get default audio parameters for sub-objects of composite objects.
- Added test controller: `composite_object_test.py` Test if the avatar can grasp a sub-object of a composite object.
- Added: `composite_object_audio.json` Audio values for every sub-object of a composite object.

## 0.3.2

### Frontend

- `StickyMittenAvatarController`:
  - Added required parameter `arm` to `grasp_object()` (the function no longer chooses the arm closet to the target)
  - `grasp_object()` chooses a target position with a raycast instead of just choosing the center of the object.
  - `grasp_object()` returns no longer returns an `Arm` (just a `TaskStatus`).
  - Fixed: Various errors when trying to collect avatar data if there is no avatar.
  - Fixed: The angle used to calculate rotation from the avatar's forward directional vector is often incorrect.
  - Fixed: `turn_to()` and `turn_by()` sometimes don't stop at the correct angle.
  - Fixed: `turn_to()`, `turn_by()`, `go_to`, and `move_forward_by()` often set an incorrect target position if supplied an object ID.
- Removed: `TaskStatus.turned_360` (not needed).
- `shake_demo.py` works more reliably.

### Backend

- Added: `turn_test.py` Test avatar turning.

## 0.3.1

### Frontend

- Moved changelog to this document.
- Allow simpler import statements: `from sticky_mitten_avatar import Arm, TestController`
- `StickyMittenAvatarController`:
  - Replaced `frame` (a single `FrameData` object) with `frames` (all `FrameData` since the start of the previous action).
  - Renamed: `pick_up()` to `grasp_object()`
  - Renamed: `put_down()` to `drop()`
  - **All API calls that returned a `bool` now return a `TaskStatus` instead.**
  - Updated all example code for the API document.
  - Documentation lists all possible `TaskStatus` values per function.
  - Renamed: `tap()` to `_tap()` (hides it from the API, for now).
- `FrameData`:
  - Added: `held_objects` A dictionary of IDs of objects held in each mitten.
  - Added: `image_pass` The `_img` pass.
  - Added: `set_surface_material()` Set the surface (floor) material.
  - `get_pil_images()` returns a dictionary instead of a tuple where key = the name of the image pass.
  - Removed: `AvatarCollisions` type and `FrameData.avatar_collisions`. The same data is now split between `FrameData.avatar_object_collisions` and `FrameData.avatar_env_collisions`.
  - Updated all example code for the API document.
- Added: `TaskStatus`. The current status of the avatar.
- Fixed: `collision_test.py` and `ik_unit_tests.py` won't run.
- Fixed: API document doesn't display `__init__` functions correctly.
- Added: clearer example code to the README.
- Removed: `fail_state.md` (redundant)


### Backend

- Changed maximum shoulder roll angle to 45 (was 90).
- Removed `surface_material` parameter from the `FrameData` constructor.
- Removed: `dynamic_object_info.py`
- Removed backend API documents.

***

## 0.3.0

### High-Level

- Each API call returns a `TaskStatus` instead of a `bool`. The `TaskStatus` indicates whether the task was a success and if not, why.
- There is always exactly 1 avatar per scene.
  - Removed `avatar_id` parameter from all API and output data. 
  - `FrameData.avatar_collision` is an `AvatarCollisions` object (was a dictionary mapped to avatar IDs)
  - `StickyMittenAvatarController.static_avatar_data` is a dictionary of `BodyPartStatic` (was a dictionary of dictionaries, mapped to avatar IDs)
- Better formatting for API document headers.
- Cleaned up API section of README document.
- Removed: `fail_state.md`
- `StickyMittenAvatarController.md` (API document) includes all possible `TaskStatus` return values per function.

***

## 0.2.3

### High-Level

- Added: `StickyMittenAvatarController.tap()`
- `avatar_id` parameter of all API functions in `StickyMittenAvatarController` has a default value of `"a"`
- Renamed: `StickyMittenAvatarController.bend_arm()` to `StickyMittenAvatarController.reach_for_target()`
- Added optional parameter `check_if_possible` to `StickyMittenAvatarController.reach_for_target()`
- `StickyMittenAvatarController` gathers `_id` and `_depth_simple` image passes instead of `_img` and `_id`.
- Fixed: `put_object_in_container.py` doesn't work.
- `FrameData` records audio due to collisions with avatar body parts.
- Renamed: `FrameData.segmentation_image` to `FrameData.id_pass`
- Renamed: `FrameData.depth_map` to `FrameData.depth_pass`
  - `FrameData.depth_pass` can be converted to a grayscale image instead of being a numpy array of floats
- Added: `FrameData.save_images()`
- Added: `FrameData.get_pil_images()`
- Added test controller: `tap.py`
- Added video: `put_object_in_container.mp4`

### Low-Level

- Renamed: `Avatar.can_bend_to()` to `Avatar.can_reach_target()`
- Fixed: `Avatar.can_bend_to()` is inaccurate.

***

## 0.2.2

### High-Level

- Made the following functions in `StickyMittenAvatarController` private (added a `_` prefix), thereby hiding them from the API:
  - `_create_avatar()`
  - `get_add_object()` (renamed to `_add_object()`)
  - `get_add_container()` (renamed to `_add_container()`)
  - `_do_joint_motion()`
  - `_stop_avatar()`
  - `_destroy_avatar()`
- Set a default value for the `avatar_id` for most `StickyMittenAvatarController` API calls.
- Added: `StickyMittenAvatarController.static_avatar_data`.
- Added: `StickyMittenAvatar.rotate_camera_by()`.
- Added: `StickyMittenAvatar.reset_camera_rotation()`.
- Removed: `StickyMittenAvatarController.get_container_records()`
- Removed: `StickyMittenAvatarController.on_resp` (functionality can be replicated with `Controller.communite()`)
- Added field `name` to `BodyPartStatic`.
- Added field `audio` to `BodyPartStatic`.
- Moved `BodyPartStatic` to `body_part_static.py`.
- Removed `FrameData.images` and added: `FrameData.segmentation_image` (a PIL image) and `FrameData.depth_map` (a numpy array).
- Added field `avatar_collisions` to `FrameData`. Collisions per avatar between its body parts and other objects or the environment.
- Set the maximum shoulder roll angle to 90 degrees (was 45 degrees).
- Added: `collision_test.py` Test for the avatar listening to collisions.
- Added: `test_controller.py` Initialize a simple scene and an avatar in debug mode. 
- Removed private functions from API documentation.
- Added example code to `FrameData` documentation.
- Various improvements to `StickyMittenAvatar` API documentation.
- Added: `fail_state.md` document to explain fail states.
- Updated `shake_demo.mp4`

#### Low-Level

- Added: `Avatar.can_bend_to()` True if the avatar can bend the arm to the target (assuming no obstructions or other factors).

***

## 0.2.1

### High-Level

- Improved the overall stability of `shake_demo.py`
- Improved the positional accuracy of arm-bending API calls  by matching the IK parameters more closely to the avatar prefab parameters.
- Fixed: The default speed of `StickyMittenAvatarController.turn_to()` is slower than the turn speed in `StickyMittenAvatarController.go_to()`.
- `StickyMittenAvatarController.bend_arm()` will increase the force and decrease the damper of all joints that are bending. When they are done bending, they will revert to the original values.
- Added: `videos/shake_demo.mp4`

### Low-Level

- Avatar IK arm chains now include `mitten`, the centerpoint of the mitten.
- `Avatar.is_holding()` return a boolean and the arm holding the item (instead of just a boolean).

***

## 0.2.0

- Parameter `target` in `Avatar.bend_arm` must be a numpy array (previously, could be a numpy array or a list).
- Added: `Avatar.reset_arms()` Set the arms to a "neutral" position.
- Added: `Avatar.set_dummy_ik_goals()` Set "dummy" IK goals with no targets.
- Added: `box_room_containers.py` Creates a photorealistic scene with furniture and containers.
- **Added: `shake_demo.py`. The avatar shakes containers and "listens" to the audio.**
- Renamed: `PhysicsInfo` to `DynamicObjectInfo`
- Added: `FrameData` **Contains image and audio data.**
- Added new fields to `StickyMittenAvatarController`:
  - `frame` Current frame data. 
  - `static_object_info` Static object info per object.
  - Added parameter to `StickyMittenAvatarController` constructor: `audio_playback_mode`
- Added: `StickyMittenAvatar.init_scene()` Initialize a scene.
- Changed the commands returned by `StickyMittenAvatar.get_add_object()`
- Added: `StickyMittenAvatar.get_container_records()` Get records for all container models.
- Added: `StickyMittenAvatar.get_add_container()` Add a container to the scene.
- Added: `StickyMittenAvatar.reset_arms()`  Set the arms to a "neutral" position.
- Added: `StickyMittenAvatarController.shake()` Shake an avatar's joint.
- Added: `StickyMittenAvatarController.destroy_avatar()` Destroy the avatar.
- Added: `StickyMittenAvatarController.end()` End the simulation.
- Added parameter `do_motion` to `StickyMittenAvatar.put_down()`
- Parameter `target` in `StickyMittenAvatar.turn_to()` must be a dictionary (Vector3) or an integer (object ID).
- Added: `StaticObjectInfo`
- Removed: `util.get_collisions()`
- Added utility script: `add_model.py`
- Added utility script: `init_commands.py`
- Added test controller: `tests/ik_test.py`
- Removed test controller: `arm_test.py`
- Moved `put_object_in_container.py` to `controllers/` and adjusted some values to make it work with the improved IK system.
- Moved `put_object_on_table.py` to `controllers/`
- Added asset bundle `shoebox_fused`.
- Added: `audio.csv` Default audio values.
- Added model libraries: `containers.json` and `container_contents.json`
- **Fixed: IK chains for the baby avatar are wrong.**
- Fixed: `util.rotate_point_around()` often returns incorrect values.
- Fixed: `def` headers in documentation sometimes don't contain all parameters.
- Added: `videos/shake_demo.mp4`