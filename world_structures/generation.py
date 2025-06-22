import pygame
import random
import math
from .world_constants import * # Import all constants needed for generation
from .utils import is_point_in_polygon, point_segment_distance_sq # Import required utils
from .quadtree import QuadtreeNode # Needed for PDS tree generation
# No direct import of Zone needed here if generate_world_elements creates them
# and these functions just consume their polygon_points or use their methods.

# --- Grass Generation ---
def generate_grass_details(count, kingdom_zone, forest_zone):
     details = []; print(f"Generating {count} grass details (avoiding kingdom and forest)..."); placed_count = 0; attempts = 0; max_attempts = count * 20
     while placed_count < count and attempts < max_attempts:
         attempts += 1; world_x = random.randint(0, WORLD_WIDTH - 5); world_y = random.randint(0, WORLD_HEIGHT - 10)
         potential_pos = (world_x, world_y)
         # Ensure point is not exactly at origin if that's invalid
         if potential_pos != (0,0) and \
            (not kingdom_zone or not kingdom_zone.is_point_inside(potential_pos)) and \
            (not forest_zone or not forest_zone.is_point_inside(potential_pos)):
             height = random.randint(5, 10); color = random.choice([(50, 180, 50), (60, 200, 60), (40, 160, 40)])
             details.append({'rect': pygame.Rect(world_x, world_y, 2, height), 'color': color}); placed_count += 1
     if attempts >= max_attempts: print(f"Warning: Reached max attempts ({max_attempts}) placing grass. Only placed {placed_count}/{count}.")
     elif placed_count < count: print(f"Warning: Could only place {placed_count}/{count} grass details satisfying constraints.")
     else: print(f"Grass generation complete ({placed_count} details placed).")
     return details

def filter_grass_details(details, kingdom_zone, forest_zone):
    if not details: return details
    initial_count = len(details); print(f"Filtering {initial_count} loaded grass details against kingdom and forest boundaries...")
    filtered_details = []
    removed_kingdom = 0; removed_forest = 0
    for detail in details:
        # Ensure detail has a 'rect' key before accessing center
        if 'rect' in detail:
             in_kingdom = kingdom_zone and kingdom_zone.is_point_inside(detail['rect'].center)
             in_forest = forest_zone and forest_zone.is_point_inside(detail['rect'].center)
             if not in_kingdom and not in_forest: filtered_details.append(detail)
             elif in_kingdom: removed_kingdom += 1
             elif in_forest: removed_forest += 1
        else:
             print(f"Warning: Skipping grass detail missing 'rect': {detail}")
    final_count = len(filtered_details)
    print(f"Filtered out {removed_kingdom} grass details inside kingdom and {removed_forest} inside forest. {final_count} remaining.")
    return filtered_details

# --- Tree Generation ---
def is_too_close_to_wall(point, wall_vertices, min_dist):
    """Checks if a point is closer than min_dist to any segment of the wall polygon."""
    if not wall_vertices or len(wall_vertices) < 2: return False
    min_dist_sq = min_dist * min_dist; px, py = point
    for i in range(len(wall_vertices)):
        ax, ay = wall_vertices[i]; bx, by = wall_vertices[(i + 1) % len(wall_vertices)]
        dist_sq = point_segment_distance_sq(px, py, ax, ay, bx, by)
        if dist_sq < min_dist_sq: return True
    return False

def generate_trees_poisson_disk(forest_zone, kingdom_zone, kingdom_wall_vertices,
                                min_spacing, candidates_k, wall_avoid_dist, world_rect):
    """Generates tree positions using Poisson Disk Sampling within forest, avoiding kingdom/walls."""
    print(f"Generating forest trees using Poisson Disk Sampling (min spacing: {min_spacing})...")
    forest_trees = []
    tree_colliders = []

    if not forest_zone or not forest_zone.polygon_points or len(forest_zone.polygon_points) < 3:
        print("Warning: Invalid forest zone or polygon. Cannot generate trees.")
        return forest_trees, tree_colliders

    # Calculate forest bounding box for PDS and quadtree from the zone's bounds
    forest_bbox = forest_zone.bounds

    min_spacing_sq = min_spacing * min_spacing
    active_list = []
    placed_points = []
    # Initialize quadtree for efficient proximity checks during PDS
    pds_quadtree = QuadtreeNode(forest_bbox, QT_NODE_CAPACITY) # Use QuadtreeNode from quadtree.py

    # Find a valid starting point inside the forest, outside kingdom/walls
    start_point = None; attempts = 0; max_attempts = 500
    while not start_point and attempts < max_attempts:
        attempts += 1
        px = random.uniform(forest_bbox.left, forest_bbox.right)
        py = random.uniform(forest_bbox.top, forest_bbox.bottom)
        pt = (int(px), int(py))
        if forest_zone.is_point_inside(pt) and \
           (not kingdom_zone or not kingdom_zone.is_point_inside(pt)) and \
           (not is_too_close_to_wall(pt, kingdom_wall_vertices, wall_avoid_dist)):
             start_point = pt
             placed_points.append(start_point)
             active_list.append(start_point)
             pds_quadtree.insert(start_point) # Insert uses tuple directly
             break # Found starting point
    if not start_point:
        print("Error: Could not find a valid starting point for PDS within forest boundaries after max attempts.")
        return forest_trees, tree_colliders

    # Poisson Disk Sampling main loop
    while active_list:
        active_idx = random.randrange(len(active_list))
        active_point = active_list[active_idx]
        ax, ay = active_point
        found_candidate = False
        # Generate k candidate points around the active point
        for _ in range(candidates_k):
            angle = random.uniform(0, 2 * math.pi)
            radius = random.uniform(min_spacing, 2 * min_spacing)
            cand_x = int(ax + radius * math.cos(angle))
            cand_y = int(ay + radius * math.sin(angle))
            candidate_point = (cand_x, cand_y)

            # Check if candidate is valid
            if not world_rect.collidepoint(candidate_point): continue # Outside world bounds
            if not forest_zone.is_point_inside(candidate_point): continue # Outside forest
            if kingdom_zone and kingdom_zone.is_point_inside(candidate_point): continue # Inside kingdom
            if is_too_close_to_wall(candidate_point, kingdom_wall_vertices, wall_avoid_dist): continue # Too close to wall

            # Check proximity to existing points using quadtree
            search_radius = min_spacing * 1.01 # Check slightly larger than min_spacing
            query_rect = pygame.Rect(cand_x - search_radius, cand_y - search_radius, 2 * search_radius, 2 * search_radius)
            nearby_points = pds_quadtree.query(query_rect) # Query returns tuples

            too_close = False
            for near_pt in nearby_points:
                # near_pt should be a tuple (nx, ny)
                dist_sq = (cand_x - near_pt[0])**2 + (cand_y - near_pt[1])**2
                if dist_sq < min_spacing_sq:
                    too_close = True
                    break
            if too_close: continue

            # Valid candidate found
            placed_points.append(candidate_point)
            active_list.append(candidate_point)
            pds_quadtree.insert(candidate_point) # Insert the tuple
            found_candidate = True
            break # Move to next active point

        # If no valid candidate found around this active point, remove it
        if not found_candidate:
            active_list.pop(active_idx)

    print(f"PDS finished. Placed {len(placed_points)} tree base points.")

    # Create final tree objects with colliders
    for base_point in placed_points:
        bx, by = base_point # This is the base (root) position
        # Define collider relative to the base point
        trunk_collider_width = random.randint(TRUNK_COLLIDER_WIDTH_MIN, TRUNK_COLLIDER_WIDTH_MAX)
        trunk_collider_height = random.randint(TRUNK_COLLIDER_HEIGHT_MIN, TRUNK_COLLIDER_HEIGHT_MAX)
        # Collider position (top-left) based on bottom-center anchor at base_point
        trunk_collider_left_x = bx - trunk_collider_width // 2
        trunk_collider_top_y = by - trunk_collider_height # Collider sits just above the base point
        trunk_collider_rect = pygame.Rect(trunk_collider_left_x, trunk_collider_top_y, trunk_collider_width, trunk_collider_height)

        forest_trees.append({
            'collider': trunk_collider_rect,
            'base_pos': base_point # Store base point for potential future use
        })
        tree_colliders.append(trunk_collider_rect)

    print(f"Created {len(forest_trees)} final tree objects.")
    return forest_trees, tree_colliders


# --- Wall Generation ---
def generate_wall_rects(vertices, thickness, gate_segment_index, gate_point1, gate_point2):
    """Generates COLLISION rectangles for walls, handling the gate opening."""
    rects = []; num_vertices = len(vertices); step = thickness * 0.8 # Use step smaller than thickness
    if num_vertices < 2: return rects
    for i in range(num_vertices):
        p1_v = pygame.math.Vector2(vertices[i]); p2_v = pygame.math.Vector2(vertices[(i + 1) % num_vertices])
        if i == gate_segment_index and gate_point1 and gate_point2:
            # Part 1: From segment start (p1_v) to gate start (gate_point1)
            vec1 = gate_point1 - p1_v; len1 = vec1.length()
            if len1 > 1: # Avoid division by zero / zero vector
                dir1 = vec1.normalize(); num_steps1 = int(len1 / step)
                for j in range(num_steps1 + 1):
                    # Place collision rect centered on the path
                    center_pos = p1_v + dir1 * min(j * step, len1)
                    rect = pygame.Rect(0, 0, thickness, thickness); rect.center = (int(center_pos.x), int(center_pos.y)); rects.append(rect)
            # Part 2: From gate end (gate_point2) to segment end (p2_v)
            vec2 = p2_v - gate_point2; len2 = vec2.length()
            if len2 > 1:
                dir2 = vec2.normalize(); num_steps2 = int(len2 / step)
                for j in range(num_steps2 + 1):
                    # Place collision rect centered on the path, starting from gate_point2
                    center_pos = gate_point2 + dir2 * min(j * step, len2)
                    rect = pygame.Rect(0, 0, thickness, thickness); rect.center = (int(center_pos.x), int(center_pos.y)); rects.append(rect)
            continue # Move to the next segment
        # --- Handle Normal Segment Collision Rects ---
        segment_vec = p2_v - p1_v; seg_len = segment_vec.length()
        if seg_len < 1: continue # Skip zero-length segments
        seg_dir = segment_vec.normalize(); num_steps = int(seg_len / step)
        for j in range(num_steps + 1):
            center_pos = p1_v + seg_dir * min(j * step, seg_len)
            rect = pygame.Rect(0, 0, thickness, thickness); rect.center = (int(center_pos.x), int(center_pos.y)); rects.append(rect)
    return rects

def generate_wall_tile_data_rotated(vertices, gate_segment_index, gate_point1, gate_point2, tile_size):
    """
    Calculates positions AND angles for wall tile sprites along segments,
    handling the gate and spacing based on tile_size.
    """
    wall_tiles = []
    num_vertices = len(vertices)
    horizontal_vector = pygame.math.Vector2(1, 0) # Reference for angle calculation

    kingdom_center_vec = pygame.math.Vector2(KINGDOM_CENTER_X, KINGDOM_CENTER_Y) # Use constant

    if num_vertices < 2:
        print("Warning: Not enough vertices to generate wall tiles.")
        return wall_tiles

    print(f"Generating rotated wall tile data (tile size: {tile_size})...")

    # Helper function to generate tiles along a specific vector
    def generate_tiles_along_vector(start_point, end_point, segment_sprite_key):
        tiles_for_segment = []
        segment_vec = end_point - start_point
        seg_len = segment_vec.length()

        # Skip if segment is shorter than half a tile (prevents excessive overlap/tiny segments)
        if seg_len < tile_size * 0.5: return tiles_for_segment

        seg_dir = segment_vec.normalize()
        angle = seg_dir.angle_to(horizontal_vector)
        current_dist = tile_size / 2.0 # Start placing first tile centered half a tile in

        while current_dist <= seg_len - (tile_size / 2.0) + 1: # Ensure last tile is also somewhat on the segment
            center_pos = start_point + seg_dir * current_dist
            # Use the determined sprite key for this segment
            tiles_for_segment.append({
                'pos': (int(center_pos.x), int(center_pos.y)),
                'angle': angle,
                'sprite_key': segment_sprite_key # Use passed key
            })
            current_dist += tile_size # Step by full tile size for next placement
        return tiles_for_segment

    # Iterate through wall vertex segments
    for i in range(num_vertices):
        p1_v = pygame.math.Vector2(vertices[i])
        p2_v = pygame.math.Vector2(vertices[(i + 1) % num_vertices])
        # segment_midpoint = (p1_v + p2_v) / 2 # Not strictly needed for this simplified logic

        # All kingdom walls currently use 'wall_back' sprite.
        # If front/back differentiation logic is needed, it would go here.
        chosen_sprite_key = 'wall_back'

        # --- Handle Gate Segment ---
        if i == gate_segment_index and gate_point1 and gate_point2:
            # Part 1: From segment start (p1_v) to gate start (gate_point1)
            wall_tiles.extend(generate_tiles_along_vector(p1_v, gate_point1, chosen_sprite_key))
            # Part 2: From gate end (gate_point2) to segment end (p2_v)
            wall_tiles.extend(generate_tiles_along_vector(gate_point2, p2_v, chosen_sprite_key))
            continue # Move to the next segment

        # --- Handle Normal Segment ---
        wall_tiles.extend(generate_tiles_along_vector(p1_v, p2_v, chosen_sprite_key))

    print(f"Generated {len(wall_tiles)} rotated wall tile positions.")
    return wall_tiles