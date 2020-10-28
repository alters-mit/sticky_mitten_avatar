from pathlib import Path
from pkg_resources import resource_filename

"""
Paths to files in this Python module.
"""

# The directory for all scene data.
SCENE_DATA_DIRECTORY = Path(resource_filename(__name__, "scene_data"))
# The directory of the occupancy_maps map files.
OCCUPANCY_MAP_DIRECTORY = SCENE_DATA_DIRECTORY.joinpath("occupancy_maps")
# The directory of maps of y values per floorplan.
Y_MAP_DIRECTORY = SCENE_DATA_DIRECTORY.joinpath("y_maps")
# The directory of maps of reachable surface positions.
SURFACE_MAP_DIRECTORY = SCENE_DATA_DIRECTORY.joinpath("surface_maps")
# The directory of positions where objects can be procedurally created.
OBJECT_SPAWN_MAP_DIRECTORY = SCENE_DATA_DIRECTORY.joinpath("object_spawn_maps")
# The map of positions per room per scene.
ROOM_MAP_DIRECTORY = SCENE_DATA_DIRECTORY.joinpath("room_maps")
# The path to the scene bounds data.
SCENE_BOUNDS_PATH = SCENE_DATA_DIRECTORY.joinpath("scene_bounds.json")
# The path to the spawn positions.
SPAWN_POSITIONS_PATH = SCENE_DATA_DIRECTORY.joinpath("spawn_positions.json")
# The path to object data.
OBJECT_DATA_DIRECTORY = Path(resource_filename(__name__, "object_data"))
# The path to the target objects data.
TARGET_OBJECTS_PATH = OBJECT_DATA_DIRECTORY.joinpath("target_objects.csv")
# The path to composite object audio data.
COMPOSITE_OBJECT_AUDIO_PATH = OBJECT_DATA_DIRECTORY.joinpath("composite_object_audio.json")
# The path to the visual materials for target objects.
TARGET_OBJECT_MATERIALS_PATH = OBJECT_DATA_DIRECTORY.joinpath("target_object_materials.txt")
# The path to the dictionary of surface objects.
SURFACE_OBJECT_CATEGORIES_PATH = OBJECT_DATA_DIRECTORY.joinpath("surface_object_categories.json")
