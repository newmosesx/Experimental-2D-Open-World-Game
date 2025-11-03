# This file now acts as the main coordinator for world structure generation and management.
import pygame
import random
import math
import os
import pickle

# --- Import constants ---
from world_structures.world_constants import *
from world_structures.river_generation import generate_rivers

# --- Import from custom modules ---
from world_structures.quadtree import QuadtreeNode
from world_structures.utils import is_point_in_polygon, point_segment_distance_sq
from asset.assets import load_all_sprites
from world_structures.generation import (
    generate_grass_details, filter_grass_details,
    generate_trees_poisson_disk, is_too_close_to_wall,
    generate_wall_rects, generate_wall_tile_data_rotated
)
from world_structures.world_features import Zone


# --- Import external dependencies (like dungeon generator) ---
try:
    from dungeon_gen import DungeonGenerator
except ImportError:
    print("ERROR: Could not import DungeonGenerator. Check the path.")
    # Define dummy values if import fails to avoid crashing later parts,
    # although dungeon generation will fail.
    class DungeonGenerator:
        def __init__(self, w, h): pass
        def generate_dungeon(self): return [], [] # type: ignore
    print("WARNING: Using dummy DungeonGenerator.")


# --- World Generation Orchestrator ---
def generate_world_elements(loaded_sprites):
    """Generates zones, structures, trees, walls, paths, towers and returns them."""
    print("Generating dynamic world elements...")
    kingdom_structures = []; building_colliders = []
    wall_towers = []; tower_colliders = []; kingdom_wall_rects = []; gatehouses = []; gatehouse_colliders = []
    path_info = None; path_segments = []; gate_segment_index = -1; gate_p1_world, gate_p2_world = None, None; gate_midpoint_world = None
    wall_tiles = [] # Store wall tile data (pos, angle, sprite_key)
    forest_trees = []; tree_colliders = [] # Initialize tree lists
    
    forest_zone = None
    kingdom_zone = None

    # --- Forest Zone Definition (Oval) ---
    print("Generating oval forest zone...")
    forest_poly_points = []
    angle_step = 2 * math.pi / FOREST_NUM_VERTICES
    for i in range(FOREST_NUM_VERTICES):
        current_angle = i * angle_step
        current_radius_x = FOREST_RADIUS_X + random.uniform(-FOREST_RADIUS_VARIATION, FOREST_RADIUS_VARIATION); current_radius_x = max(FOREST_RADIUS_X * 0.1, current_radius_x) # Ensure minimum size
        current_radius_y = FOREST_RADIUS_Y + random.uniform(-FOREST_RADIUS_VARIATION, FOREST_RADIUS_VARIATION); current_radius_y = max(FOREST_RADIUS_Y * 0.1, current_radius_y)
        vx = FOREST_CENTER_X + current_radius_x * math.cos(current_angle); vy = FOREST_CENTER_Y + current_radius_y * math.sin(current_angle)
        forest_poly_points.append((int(vx), int(vy)))
    forest_zone = Zone("forest", forest_poly_points, FOREST_GROUND_COLOR)


    # --- Kingdom Generation (Circular) ---
    print("Generating circular kingdom...")
    kingdom_wall_vertices = [] # These are the polygon points for the kingdom zone
    angle_step_k = 2 * math.pi / KINGDOM_NUM_VERTICES
    for i in range(KINGDOM_NUM_VERTICES):
        current_angle = i * angle_step_k
        current_radius = KINGDOM_RADIUS + random.uniform(-KINGDOM_RADIUS_VARIATION, KINGDOM_RADIUS_VARIATION)
        vx = KINGDOM_CENTER_X + current_radius * math.cos(current_angle); vy = KINGDOM_CENTER_Y + current_radius * math.sin(current_angle)
        kingdom_wall_vertices.append((int(vx), int(vy)))
    # kingdom_poly_points = kingdom_wall_vertices # Old way
    kingdom_zone = Zone("kingdom", kingdom_wall_vertices, KINGDOM_GROUND_COLOR)
    wall_verts_count = len(kingdom_wall_vertices)


    # --- Generate Kingdom Details (Towers, Gate, Path, Buildings) ---

    # --- Wall Towers ---
    tower_sprite_info = loaded_sprites.get('tower')
    if tower_sprite_info:
        for vx, vy in kingdom_wall_vertices: # Use kingdom_wall_vertices which are the kingdom zone's polygon points
            tower_base_rect = pygame.Rect(0, 0, TOWER_SIZE, TOWER_SIZE)
            tower_base_rect.center = (vx, vy)
            tower_colliders.append(tower_base_rect)
            wall_towers.append({'base_rect': tower_base_rect})
    else:
        print("Tower sprite not loaded, skipping tower placement.")

    # --- Find Gate Segment (Bottom-most) ---
    print("Finding bottom-most segment for gate placement...")
    max_y_midpoint = -float('inf')
    gate_segment_index = -1
    if wall_verts_count > 0:
        for i in range(wall_verts_count):
            p1 = pygame.math.Vector2(kingdom_wall_vertices[i])
            p2 = pygame.math.Vector2(kingdom_wall_vertices[(i + 1) % wall_verts_count])
            mid_point = (p1 + p2) / 2
            if mid_point.y > max_y_midpoint:
                max_y_midpoint = mid_point.y
                gate_segment_index = i
        if gate_segment_index == -1:
             print("Warning: Could not determine bottom segment. Defaulting to segment 0.")
             gate_segment_index = 0 # Should not happen if wall_verts_count > 0
        print(f"Selected segment {gate_segment_index} as bottom-most for gate.")
    else:
        print("Warning: No wall vertices found, cannot place gate.")
        gate_segment_index = -1

    # --- Calculate gate points (opening) ---
    if gate_segment_index != -1:
        p1_gate = pygame.math.Vector2(kingdom_wall_vertices[gate_segment_index])
        p2_gate = pygame.math.Vector2(kingdom_wall_vertices[(gate_segment_index + 1) % wall_verts_count])
        seg_mid_gate = (p1_gate + p2_gate) / 2
        seg_vec_gate = p2_gate - p1_gate
        seg_len_gate = seg_vec_gate.length()

        if seg_len_gate > GATE_OPENING_WIDTH:
             seg_dir_gate = seg_vec_gate.normalize()
             gate_p1_world = seg_mid_gate - seg_dir_gate * (GATE_OPENING_WIDTH / 2)
             gate_p2_world = seg_mid_gate + seg_dir_gate * (GATE_OPENING_WIDTH / 2)
             gate_midpoint_world = seg_mid_gate
        elif seg_len_gate > 10: # Segment too short for full opening
            print(f"Warning: Chosen gate segment {gate_segment_index} too short for desired GATE_OPENING_WIDTH ({GATE_OPENING_WIDTH}). Making opening equal to segment length.")
            gate_p1_world = p1_gate; gate_p2_world = p2_gate; gate_midpoint_world = seg_mid_gate
        else: # Segment extremely short
             print(f"Warning: Gate segment {gate_segment_index} is extremely short ({seg_len_gate:.1f}px). Disabling gate opening.")
             gate_segment_index = -1; gate_p1_world, gate_p2_world, gate_midpoint_world = None, None, None # type: ignore
    else: # No gate segment found
        gate_p1_world, gate_p2_world, gate_midpoint_world = None, None, None # type: ignore


    # --- Generate Rotated Wall Tile Data using imported function ---
    if loaded_sprites.get('wall_back'):
         wall_tiles = generate_wall_tile_data_rotated( 
             kingdom_wall_vertices, # Pass the vertices directly
             gate_segment_index,
             gate_p1_world,
             gate_p2_world,
             WALL_TILE_SIZE
         )
    else:
         print("Wall sprites not loaded, skipping wall tile generation.")


    # --- Generate wall COLLISION rects using imported function ---
    if gate_segment_index != -1 and gate_p1_world and gate_p2_world:
        print(f"Generating wall collision rects with opening at segment {gate_segment_index}")
        kingdom_wall_rects = generate_wall_rects( 
            kingdom_wall_vertices, KINGDOM_WALL_THICKNESS, gate_segment_index, gate_p1_world, gate_p2_world
        )
    else: # No gate opening (either segment_index is -1, or p1/p2 are None)
        print("Generating solid wall collision rects (no gate opening).")
        # Ensure gate_p1/p2 are None if there's no opening, even if segment_index was valid but opening calc failed
        actual_gate_p1 = gate_p1_world if gate_segment_index != -1 else None
        actual_gate_p2 = gate_p2_world if gate_segment_index != -1 else None
        actual_gate_segment_index = gate_segment_index if actual_gate_p1 and actual_gate_p2 else -1

        kingdom_wall_rects = generate_wall_rects( 
            kingdom_wall_vertices, KINGDOM_WALL_THICKNESS, actual_gate_segment_index, actual_gate_p1, actual_gate_p2
        )

    # --- Single Gatehouse at Midpoint ---
    gatehouse_sprite_info = loaded_sprites.get('gatehouse')
    if gate_segment_index != -1 and gate_midpoint_world and gatehouse_sprite_info:
        print("Placing single gatehouse...")
        gh_base_width = GATEHOUSE_SIZE; gh_base_height = GATEHOUSE_SIZE
        gatehouse_base_rect = pygame.Rect(0, 0, gh_base_width, gh_base_height)
        gatehouse_base_rect.center = (int(gate_midpoint_world.x), int(gate_midpoint_world.y))
        gatehouse_colliders.append(gatehouse_base_rect)
        gatehouses.append({'base_rect': gatehouse_base_rect})
        print(f"Gatehouse added at {gatehouse_base_rect.center}")
    elif gatehouse_sprite_info is None:
        print("Gatehouse sprite not loaded, skipping gatehouse placement.")
    elif gate_segment_index == -1 or not gate_midpoint_world:
        print("No valid gate midpoint for gatehouse placement.")


    # --- Main Path ---
    if gate_midpoint_world:
        print(f"Generating path from gate midpoint: {gate_midpoint_world}")
        path_start_point = gate_midpoint_world
        path_end_point = pygame.math.Vector2(KINGDOM_CENTER_X, KINGDOM_CENTER_Y)
        path_info = { "start": (int(path_start_point.x), int(path_start_point.y)), "end": (int(path_end_point.x), int(path_end_point.y)), "width": PATH_WIDTH, "color": PATH_COLOR }
        path_segments.append((path_start_point.x, path_start_point.y, path_end_point.x, path_end_point.y))
    else:
        print("No gate midpoint available, path not generated.")


    # --- Generate Buildings ---
    print("Generating kingdom buildings (avoiding path and walls)...")
    attempts = 0; buildings_placed = 0
    max_extent = KINGDOM_RADIUS + KINGDOM_RADIUS_VARIATION; min_build_x = KINGDOM_CENTER_X - max_extent; max_build_x = KINGDOM_CENTER_X + max_extent; min_build_y = KINGDOM_CENTER_Y - max_extent; max_build_y = KINGDOM_CENTER_Y + max_extent
    building_sprite_info = loaded_sprites.get('building')

    if building_sprite_info and kingdom_zone: # Ensure kingdom_zone exists
        while buildings_placed < KINGDOM_BUILDING_COUNT and attempts < KINGDOM_BUILDING_COUNT * 30:
            attempts += 1
            b_base_width = random.randint(BUILDING_BASE_WIDTH_MIN, BUILDING_BASE_WIDTH_MAX)
            b_base_height = random.randint(BUILDING_BASE_HEIGHT_MIN, BUILDING_BASE_HEIGHT_MAX)
            world_x = random.randint(int(min_build_x), int(max_build_x - b_base_width))
            world_y = random.randint(int(min_build_y), int(max_build_y - b_base_height))
            b_base_rect = pygame.Rect(world_x, world_y, b_base_width, b_base_height)
            building_center = b_base_rect.center

            # Check if center is within kingdom zone
            if not kingdom_zone.is_point_inside(building_center): continue

            # Check distance to path
            if path_segments:
                try:
                    # from world_structures.utils import point_segment_distance_sq # Already imported at top
                    min_dist_sq_to_path = float('inf')
                    for seg in path_segments: min_dist_sq_to_path = min(min_dist_sq_to_path, point_segment_distance_sq(building_center[0], building_center[1], seg[0], seg[1], seg[2], seg[3]))
                    if min_dist_sq_to_path < PATH_AVOIDANCE_RADIUS**2: continue
                except ImportError: # Should not happen due to top-level import
                    print("Warning: point_segment_distance_sq not found, cannot check building distance to path.")
                    pass 


            # Check distance to wall segments (using imported is_too_close_to_wall logic)
            if is_too_close_to_wall(building_center, kingdom_wall_vertices, WALL_AVOIDANCE_BUILDING):
                 continue # Too close to wall

            # Check overlap with existing buildings, towers, gatehouses (using inflated rect for spacing)
            overlapped = False; check_colliders = building_colliders + tower_colliders + gatehouse_colliders
            inflated_check_rect = b_base_rect.inflate(BUILDING_SPACING, BUILDING_SPACING)
            for existing_collider in check_colliders:
                if inflated_check_rect.colliderect(existing_collider):
                    overlapped = True; break
            if overlapped: continue

            # Placement successful
            building_colliders.append(b_base_rect)
            buildings_placed += 1
            kingdom_structures.append({'base_rect': b_base_rect}) # Store base rect

        if attempts >= KINGDOM_BUILDING_COUNT * 30: print(f"Warning: Reached max attempts placing buildings. Only placed {buildings_placed}/{KINGDOM_BUILDING_COUNT}.")
        else: print(f"Placed {buildings_placed} buildings.")
    elif not building_sprite_info:
        print("Building sprite not loaded, skipping building placement.")
    elif not kingdom_zone:
        print("Kingdom zone not defined, skipping building placement.")


    # --- Forest Tree Generation using imported function ---
    world_boundary_rect = pygame.Rect(0, 0, WORLD_WIDTH, WORLD_HEIGHT)
    tree_sprite_info = loaded_sprites.get('tree')

    if tree_sprite_info and forest_zone and kingdom_zone: # Check if sprites and zones loaded
         forest_trees, tree_colliders = generate_trees_poisson_disk( 
             forest_zone=forest_zone, kingdom_zone=kingdom_zone, kingdom_wall_vertices=kingdom_wall_vertices, # Pass Zone objects
             min_spacing=MIN_TREE_SPACING, candidates_k=PDS_CANDIDATES, wall_avoid_dist=WALL_AVOIDANCE_TREE, world_rect=world_boundary_rect
         )
    else:
         if not tree_sprite_info: print("Tree sprite not loaded, skipping tree generation.")
         if not forest_zone: print("Forest zone not defined, skipping tree generation.")
         if not kingdom_zone: print("Kingdom zone not defined, skipping tree generation (needed for avoidance).")
         forest_trees, tree_colliders = [], [] 


    # --- Final Collation ---
    print("Static world element generation complete.")
    all_colliders = tree_colliders + kingdom_wall_rects + building_colliders + tower_colliders + gatehouse_colliders

    return {
        "forest_zone": forest_zone, "forest_trees": forest_trees, # Store Zone object
        "kingdom_zone": kingdom_zone, "kingdom_wall_vertices": kingdom_wall_vertices, # Store Zone object, keep vertices for now for wall gen
        "kingdom_structures": kingdom_structures, # Buildings
        "gate_info": {"segment_index": gate_segment_index, "p1": gate_p1_world, "p2": gate_p2_world, "mid": gate_midpoint_world},
        "colliders": all_colliders, # Combined collision shapes
        "wall_tiles": wall_tiles, # Visual wall tile data (pos, angle, sprite_key)
        "wall_towers": wall_towers,
        "gatehouses": gatehouses,
        "path_info": path_info,
        # Keep separate lists for potential specific uses
        "tree_colliders_only": tree_colliders,
        "building_colliders_only": building_colliders,
        "wall_colliders_only": kingdom_wall_rects, # Collision rects
        "tower_colliders_only": tower_colliders,
        "gatehouse_colliders_only": gatehouse_colliders,
        "loaded_sprites": loaded_sprites # Pass loaded sprites through
    }


# --- World Loading / Saving ---
def load_or_generate_world():
    """Loads world data or generates it if necessary."""

    # Load sprites first using the dedicated function from asset.assets
    loaded_sprites = load_all_sprites() # This should call the one in asset.assets

    # Check if essential water sprite loaded before proceeding with river
    water_sprite_info = loaded_sprites.get('water_texture')
    river_data_dict = {'tile_positions': [], 'centerline_path': []} # Default empty
    if not water_sprite_info:
        print("--- ABORTING RIVER GEN --- Water tile sprite not loaded.")
    else:
        print("Generating river details...")
        river_data_dict = generate_rivers(water_sprite_info) # Returns dict with tile_pos and centerline_path

    print("Generating core world elements (zones, structures)...")
    world_elements = generate_world_elements(loaded_sprites)

    # Add the generated river data to the main world elements dictionary
    world_elements["rivers"] = river_data_dict

    # --- Grass Details (Load or Generate) ---
    grass_details = None
    if os.path.exists(SAVE_FILE_GRASS):
        print(f"Loading grass details from {SAVE_FILE_GRASS}...");
        try:
            with open(SAVE_FILE_GRASS, 'rb') as f: loaded_grass_details = pickle.load(f)
            print(f"Loaded {len(loaded_grass_details)} grass details.")
            # Filter loaded grass against current kingdom/forest zones using imported function
            grass_details = filter_grass_details(loaded_grass_details, world_elements.get("kingdom_zone"), world_elements.get("forest_zone"))
        except Exception as e: print(f"Error loading grass data: {e}. Regenerating..."); grass_details = None

    if grass_details is None: # If loading failed or file didn't exist
        # Generate grass using imported function, passing Zone objects
        grass_details = generate_grass_details(GRASS_DETAIL_COUNT, world_elements.get("kingdom_zone"), world_elements.get("forest_zone"))
        # Save generated grass
        try:
            with open(SAVE_FILE_GRASS, 'wb') as f: pickle.dump(grass_details, f)
            print(f"Saved generated grass data to {SAVE_FILE_GRASS}.")
        except Exception as e: print(f"Error saving grass data: {e}")

    world_elements["grass_details"] = grass_details # Add grass to the world elements dict

    # --- Dungeon Generation ---
    print("Generating dungeon layout...")
    dungeon_gen = DungeonGenerator(DUNGEON_GRID_WIDTH, DUNGEON_GRID_HEIGHT)
    dungeon_grid_data, dungeon_room_rects_grid = dungeon_gen.generate_dungeon()
    world_elements["dungeon_grid"] = dungeon_grid_data
    world_elements["dungeon_rooms_grid"] = dungeon_room_rects_grid
    print(f"Dungeon generated with {len(dungeon_room_rects_grid)} rooms.")

    # --- Prepare Quadtree ---
    print("Preparing Quadtree for population...");
    world_boundary_rect = pygame.Rect(0, 0, WORLD_WIDTH, WORLD_HEIGHT)
    collision_quadtree = QuadtreeNode(world_boundary_rect, QT_NODE_CAPACITY)
    # Population happens in main game loop based on game state

    return world_elements, collision_quadtree


# --- Quadtree Population Helpers ---
# These remain here as they are closely tied to the world structure setup
def populate_quadtree_with_dungeon(quadtree, dungeon_grid):
    """Populates the quadtree with wall tiles from the dungeon grid."""
    quadtree.items = []; quadtree.divided = False; quadtree.north_west = quadtree.north_east = quadtree.south_west = quadtree.south_east = None # Reset tree
    insert_count = 0; fail_count = 0
    print("Populating Quadtree with Dungeon Walls...")
    if not dungeon_grid:
        print("Warning: No dungeon grid provided for quadtree population.")
        return
    for y, row in enumerate(dungeon_grid):
        for x, tile_type in enumerate(row):
            if tile_type == TILE_WALL: # Use constant
                wall_world_x = x * DUNGEON_TILE_SIZE; wall_world_y = y * DUNGEON_TILE_SIZE
                wall_rect = pygame.Rect(wall_world_x, wall_world_y, DUNGEON_TILE_SIZE, DUNGEON_TILE_SIZE)
                if quadtree.boundary.colliderect(wall_rect): # Basic check
                    if wall_rect.width > 0 and wall_rect.height > 0: # Ensure valid rect
                         if quadtree.insert(wall_rect): insert_count += 1
                         else: print(f"ERROR: Failed Quadtree insert for dungeon wall: {wall_rect}"); fail_count += 1
                    else: fail_count +=1 # Invalid rect
    print(f"Dungeon Quadtree population complete. Inserted: {insert_count}, Failed/Skipped: {fail_count}")

def populate_quadtree_with_overworld(quadtree, overworld_colliders):
    """Populates the quadtree with colliders from the overworld elements."""
    quadtree.items = []; quadtree.divided = False; quadtree.north_west = quadtree.north_east = quadtree.south_west = quadtree.south_east = None # Reset tree
    insert_count = 0; fail_count = 0;
    print("Populating Quadtree with Overworld Colliders...")
    if not overworld_colliders:
        print("Warning: No colliders provided for overworld quadtree population.")
        return
    for original_collider_rect in overworld_colliders:
        if not isinstance(original_collider_rect, pygame.Rect):
             print(f"Warning: Skipping invalid collider item: {original_collider_rect}")
             fail_count += 1; continue
        if original_collider_rect.width <= 0 or original_collider_rect.height <= 0: # Check for invalid rects
            fail_count += 1; continue
        # Clamp collider rects to the quadtree boundary before insertion
        clamped_rect = original_collider_rect.clamp(quadtree.boundary)
        if clamped_rect.width > 0 and clamped_rect.height > 0: # Ensure clamped rect is still valid
            if quadtree.insert(clamped_rect): insert_count += 1
            else: print(f"ERROR: Failed Quadtree insert even after clamping: {clamped_rect} (Original: {original_collider_rect})"); fail_count += 1
        else: fail_count += 1 # Clamped rect became invalid
    print(f"Overworld Quadtree population complete. Inserted: {insert_count}, Failed/Skipped: {fail_count}")
