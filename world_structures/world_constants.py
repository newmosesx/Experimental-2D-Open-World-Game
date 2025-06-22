import os
import random
from paths import WALL_SPRITE_DIR, TREE_SPRITE_DIR

# --- Seed for Consistent Randomness ---
RANDOM_SEED = 1337
random.seed(RANDOM_SEED) # Seed should be set early


# --- Animation Speed ---
ANIMATION_SPEED_MS = 150 

# --- Screen & General ---
SCREEN_WIDTH = 1370
SCREEN_HEIGHT = 720
FPS = 60

# --- Player ---
PLAYER_RADIUS = 8
PLAYER_SPEED = 6
PLAYER_COLOR = (220, 0, 0)
# <<< Player Base Stats >>>
PLAYER_BASE_HEALTH = 100
PLAYER_BASE_DEFENSE = 0.05
PLAYER_BASE_AGILITY = 0.08
PLAYER_MAX_DEFENSE = 0.90
PLAYER_MAX_AGILITY = 0.60
# --- End Player Stats ---

# --- World & Camera ---
WORLD_WIDTH = 20000
WORLD_HEIGHT = 20000
SAVE_FILE_GRASS = "world_grass.pkl"

# --- Zone Definitions ---
FOREST_CENTER_X = WORLD_WIDTH // 2
FOREST_CENTER_Y = WORLD_HEIGHT // 3
FOREST_RADIUS_X = WORLD_WIDTH // 3
FOREST_RADIUS_Y = WORLD_HEIGHT // 5
FOREST_RADIUS_VARIATION = 800
FOREST_NUM_VERTICES = 80
KINGDOM_CENTER_X = WORLD_WIDTH // 5
KINGDOM_CENTER_Y = WORLD_HEIGHT // 2
KINGDOM_RADIUS = 3000
KINGDOM_RADIUS_VARIATION = 250
KINGDOM_NUM_VERTICES = 60

# --- Colors ---
GRASS_COLOR_BASE = (34, 139, 34)
FOREST_GROUND_COLOR = (0, 100, 0)
KINGDOM_GROUND_COLOR = (160, 160, 160)
PATH_COLOR = (190, 190, 190)
RIVER_COLOR = (0, 0, 200) 
# Dungeon Colors (Imported from dungeon_gen originally, keep here for drawing)
DUNGEON_COLOR_FLOOR = (50, 50, 50)
DUNGEON_COLOR_WALL = (100, 100, 100)

# --- Detail Generation Constants ---
GRASS_DETAIL_COUNT = 10000
KINGDOM_BUILDING_COUNT = 45
KINGDOM_WALL_THICKNESS = 35 # Keep for collision rect generation
GATE_OPENING_WIDTH = 180
WALL_TILE_SIZE = 48 # Actual pixel dimension of wall sprites

WALL_AVOIDANCE_BUILDING = KINGDOM_WALL_THICKNESS * 2.5
WALL_AVOIDANCE_TREE = KINGDOM_WALL_THICKNESS * 2.0
PATH_WIDTH = 50
BUILDING_SPACING = 25
PATH_AVOIDANCE_RADIUS = PATH_WIDTH * 1.2
GATEHOUSE_SIZE = KINGDOM_WALL_THICKNESS * 1.8
TOWER_SIZE = KINGDOM_WALL_THICKNESS * 1.4

# --- Tree Sprite Constants ---
TREE_ASSET_PATH = os.path.join(TREE_SPRITE_DIR)
MIN_TREE_SPACING = 140
PDS_CANDIDATES = 15
TRUNK_COLLIDER_HEIGHT_MIN, TRUNK_COLLIDER_HEIGHT_MAX = 15, 25
TRUNK_COLLIDER_WIDTH_MIN, TRUNK_COLLIDER_WIDTH_MAX = 8, 14

# --- Structure Sprite Constants ----
WALL_SPRITE_BACK_PATH = os.path.join(WALL_SPRITE_DIR)

BUILDING_BASE_WIDTH_MIN, BUILDING_BASE_WIDTH_MAX = 40, 65
BUILDING_BASE_HEIGHT_MIN, BUILDING_BASE_HEIGHT_MAX = 35, 60

# --- Map Constants ---
MAP_OUTPUT_FILENAME = "generated_world_map.png"
MAP_SCALE_FACTOR = 1.0 # KEEP AT 1.0 for now. If changed, needs to be less than 1.0 (e.g. 0.1 for 10% size)
MAP_GATEHOUSE_COLOR = (100, 0, 0)
MAP_WIDTH = 200 # On-screen mini-map width
MAP_HEIGHT = MAP_WIDTH # On-screen mini-map height
MAP_X = SCREEN_WIDTH - MAP_WIDTH - 10
MAP_Y = 10
MAP_BG_COLOR = (100, 100, 100, 200)
MAP_BORDER_COLOR = (255, 255, 255)
MAP_PLAYER_COLOR = (255, 0, 0)
MAP_PLAYER_SIZE = 2
MAP_ZONE_FOREST_COLOR = (0, 80, 0, 180)
MAP_ZONE_KINGDOM_COLOR = (130, 130, 130, 180)
MAP_PATH_COLOR = (210, 210, 210, 200)
MAP_TOWER_COLOR = (60, 60, 60, 200)


# --- River Constants ---
MAP_RIVER_COLOR = (50, 50, 220, 200) # Color for river on the static map image and mini-map
RIVER_WIDTH = 15 # General width for river on map (deprecated by MAP_RIVER_WIDTH for map drawing)
MAP_RIVER_WIDTH = 2 # Pixel width of the river line on the static map image and mini-map

# Procedural River Generation Parameters
RIVER_START_Y_FRAC = 0.1 # Start river near this fraction of world height
RIVER_END_Y_FRAC = 0.9   # End river near this fraction of world height
RIVER_BASE_WIDTH = 250   # Average width in pixels for tile placement
RIVER_WAVINESS_AMPLITUDE = 350 # How much it deviates left/right from center
RIVER_WAVINESS_FREQUENCY = 400.0 # Larger = longer, gentler bends
RIVER_WIDTH_VARIATION = 60 # How much width changes along the river
RIVER_WIDTH_VAR_FREQ = 250.0 # Frequency of width changes
RIVER_CENTER_X_START_OFFSET = - WORLD_WIDTH * 0.15 # Start river offset from world center X
RIVER_CENTER_X_END_OFFSET = WORLD_WIDTH * 0.1 # End river offset from world center X
RIVER_CENTERLINE_STEP_Y = 50 # How often (in world pixels Y-direction) to sample a point for the river's centerline path (for map)


# Quadtree Constants
QT_NODE_CAPACITY = 4
QT_MAX_DEPTH = 10

# Dungeon Constants (Imported from dungeon_gen originally)
# Need these for quadtree population and potentially drawing logic
DUNGEON_TILE_SIZE = 32
TILE_FLOOR = 0
TILE_WALL = 1
DUNGEON_GRID_WIDTH = 150 # Example, match dungeon_gen
DUNGEON_GRID_HEIGHT = 150 # Example, match dungeon_gen