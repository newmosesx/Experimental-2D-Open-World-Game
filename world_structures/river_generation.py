# --- START OF FILE river_generation.py ---
import pygame
import math
import random # Make sure random is imported

# Import necessary constants
# Adjust the path based on your project structure
from .world_constants import (
    WORLD_WIDTH, WORLD_HEIGHT,
    RIVER_BASE_WIDTH, RIVER_WAVINESS_AMPLITUDE, RIVER_WAVINESS_FREQUENCY,
    RIVER_WIDTH_VARIATION, RIVER_WIDTH_VAR_FREQ,
    RIVER_START_Y_FRAC, RIVER_END_Y_FRAC,
    RIVER_CENTER_X_START_OFFSET, RIVER_CENTER_X_END_OFFSET,
    RIVER_CENTERLINE_STEP_Y
)
# Note: We don't import RIVER_COLOR or RIVER_WIDTH here as we use the texture

def generate_rivers(water_sprite_info):
    """
    Generates river tile positions for sprite rendering and a centerline path for map drawing.
    Requires info about the loaded water tile sprite.
    """
    print("Generating procedural river layout and centerline...")
    river_tile_positions = []
    centerline_path_points = [] # For map drawing

    if not water_sprite_info or 'surface' not in water_sprite_info:
        print("--- ERROR --- Water sprite info not provided or invalid. Cannot generate river tiles.")
        return {'tile_positions': [], 'centerline_path': []}

    tile_width = water_sprite_info['width']
    tile_height = water_sprite_info['height']

    if tile_width <= 0 or tile_height <= 0:
         print(f"--- ERROR --- Invalid water tile dimensions ({tile_width}x{tile_height}). Cannot generate river tiles.")
         return {'tile_positions': [], 'centerline_path': []}

    print(f"Using water tile size: {tile_width}x{tile_height} for river sprite placement.")

    # Define start and end Y coordinates for the river's main flow
    start_y_world = WORLD_HEIGHT * RIVER_START_Y_FRAC
    end_y_world = WORLD_HEIGHT * RIVER_END_Y_FRAC
    river_length_y_world = end_y_world - start_y_world

    if river_length_y_world <= 0:
         print("--- ERROR --- River start Y is not before end Y. Check RIVER_START_Y_FRAC and RIVER_END_Y_FRAC.")
         return {'tile_positions': [], 'centerline_path': []}

    # Iterate for centerline path generation (coarser steps)
    # And also for tile placement (finer steps for tiles)
    
    # Determine the overall Y range for iteration for both centerline and tiles
    # Extend slightly beyond start/end to ensure full coverage if waviness is large
    # Iteration_start_y should ensure the first centerline point is at or before start_y_world
    # Iteration_end_y should ensure the last centerline point is at or after end_y_world
    iteration_start_y = int(start_y_world - RIVER_WAVINESS_AMPLITUDE)
    iteration_end_y = int(end_y_world + RIVER_WAVINESS_AMPLITUDE)


    # --- Generate Centerline Path (Coarser Steps) ---
    # Use RIVER_CENTERLINE_STEP_Y for stepping through the river's main flow direction
    # Ensure this step is at least 1
    centerline_step = max(1, RIVER_CENTERLINE_STEP_Y) 
    print(f"Generating river centerline with step_y = {centerline_step}")

    world_center_x = WORLD_WIDTH / 2.0
    start_center_x_abs = world_center_x + RIVER_CENTER_X_START_OFFSET
    end_center_x_abs = world_center_x + RIVER_CENTER_X_END_OFFSET

    # Iterate for centerline points
    # current_y_for_centerline starts from the actual river_start_y
    for current_y_for_centerline in range(int(start_y_world), int(end_y_world) + 1, centerline_step):
        # Calculate y_progress relative to the defined river start/end, not the iteration bounds
        y_progress = max(0.0, min(1.0, (current_y_for_centerline - start_y_world) / river_length_y_world))

        target_center_x = start_center_x_abs + (end_center_x_abs - start_center_x_abs) * y_progress
        waviness_offset = RIVER_WAVINESS_AMPLITUDE * math.sin( (current_y_for_centerline / RIVER_WAVINESS_FREQUENCY) * 2 * math.pi )
        actual_river_center_x = target_center_x + waviness_offset
        centerline_path_points.append((int(actual_river_center_x), int(current_y_for_centerline)))
    
    # Ensure the very last point of the river is added if step doesn't align perfectly
    if not centerline_path_points or centerline_path_points[-1][1] < end_y_world:
        y_progress = 1.0 # At the end
        target_center_x = start_center_x_abs + (end_center_x_abs - start_center_x_abs) * y_progress
        waviness_offset = RIVER_WAVINESS_AMPLITUDE * math.sin( (end_y_world / RIVER_WAVINESS_FREQUENCY) * 2 * math.pi )
        actual_river_center_x = target_center_x + waviness_offset
        centerline_path_points.append((int(actual_river_center_x), int(end_y_world)))


    # --- Generate Tile Positions (Finer Steps) ---
    # Step by a fraction of tile dimensions for denser placement for sprites
    tile_placement_step_y = max(1, tile_height // 3) # Smaller step for better sprite coverage
    tile_placement_step_x = max(1, tile_width // 3)
    print(f"Generating river tiles with step_x={tile_placement_step_x}, step_y={tile_placement_step_y}")

    # Iterate through potential tile grid positions along the river's general Y flow
    # Use a slightly wider Y range for tile placement to account for waviness at edges
    # ty_tile ranges from a bit before river start to a bit after river end.
    for ty_tile in range(iteration_start_y, iteration_end_y, tile_placement_step_y):
        # Calculate y_progress relative to the defined river start/end
        y_progress = max(0.0, min(1.0, (ty_tile - start_y_world) / river_length_y_world))

        target_center_x = start_center_x_abs + (end_center_x_abs - start_center_x_abs) * y_progress
        waviness_offset = RIVER_WAVINESS_AMPLITUDE * math.sin( (ty_tile / RIVER_WAVINESS_FREQUENCY) * 2 * math.pi )
        river_center_x_at_ty = target_center_x + waviness_offset

        width_variation = RIVER_WIDTH_VARIATION * math.cos( (ty_tile / RIVER_WIDTH_VAR_FREQ) * 2 * math.pi)
        current_river_width = max(tile_width, RIVER_BASE_WIDTH + width_variation)

        river_left_bound = river_center_x_at_ty - current_river_width / 2
        river_right_bound = river_center_x_at_ty + current_river_width / 2

        check_min_x = int(river_left_bound - tile_width) # Check a bit wider for safety
        check_max_x = int(river_right_bound + tile_width)

        for tx_tile in range(check_min_x, check_max_x, tile_placement_step_x):
            tile_center_x = tx_tile + tile_width / 2.0
            # Check if this tile's center is within the river's current X bounds
            # Add a buffer (e.g., tile_width / 3) to ensure coverage near edges due to discrete steps
            if (river_left_bound - tile_width / 3) < tile_center_x < (river_right_bound + tile_width / 3):
                river_tile_positions.append((tx_tile, ty_tile))


    if tile_placement_step_x < tile_width or tile_placement_step_y < tile_height:
        print(f"Initial tile count: {len(river_tile_positions)}. Removing duplicates...")
        river_tile_positions = list(dict.fromkeys(river_tile_positions))


    print(f"Generated {len(river_tile_positions)} unique water tile positions for the river.")
    print(f"Generated {len(centerline_path_points)} points for the river centerline path.")

    return {'tile_positions': river_tile_positions, 'centerline_path': centerline_path_points}

# --- END OF FILE river_generation.py ---