import pygame
import sys
import os # Make sure os is imported
import NETconfig as network

# Import necessary components from other modules
import world_struct as world_struct_stable
import combat_mech as combat_mech_stable
import npc_system as npc_system_stable


from asset.assets import * # This imports load_all_sprites, load_sprite_sheet, constants like MUSIC_FILE_PATH etc.
from world_structures.world_constants import (MAP_SCALE_FACTOR, GRASS_COLOR_BASE, PATH_COLOR, # RIVER_COLOR deprecated for map
                                              MAP_RIVER_COLOR, MAP_RIVER_WIDTH, 
                                              MAP_OUTPUT_FILENAME, MAP_GATEHOUSE_COLOR, FOREST_GROUND_COLOR,
                                              KINGDOM_GROUND_COLOR, MAP_TOWER_COLOR)
from paths import * # Imports specific asset paths like SPRITE_SHEET_PLAYER_IDLE_FILENAME

def generate_and_save_world_map_image(world_elements, world_width, world_height):
    """
    Generates a PNG image (split into two halves vertically) of the world map
    based on world_elements. Called during the loading process.
    """
    print("-" * 30)
    print("Attempting to generate world map image...")

    # Calculate scaled dimensions
    # Ensure MAP_SCALE_FACTOR is float, typically <= 1.0
    # If MAP_SCALE_FACTOR is 1.0, scaled_width/height are same as world_width/height
    scaled_width = int(world_width * MAP_SCALE_FACTOR)
    scaled_height = int(world_height * MAP_SCALE_FACTOR)

    if scaled_width <= 0 or scaled_height <= 0:
        print(f"ERROR: Invalid scaled map dimensions ({scaled_width}x{scaled_height}) based on MAP_SCALE_FACTOR={MAP_SCALE_FACTOR}. Skipping map generation.")
        print("-" * 30)
        return

    if MAP_SCALE_FACTOR != 1.0:
        print(f"Creating SCALED world surface ({scaled_width}x{scaled_height}) for map image...")
    else:
        print(f"Creating FULL world surface ({world_width}x{world_height}) for map image...")
        print("INFO: This may require significant RAM if world dimensions are large and MAP_SCALE_FACTOR is 1.0.")

    world_surface = None 
    try:
        world_surface = pygame.Surface((scaled_width, scaled_height))
        print("Map surface created successfully.")
    except pygame.error as e:
        print(f"ERROR: Could not create Pygame surface for map: {e}")
        print("       Try reducing WORLD_WIDTH/HEIGHT or using a smaller MAP_SCALE_FACTOR (e.g., 0.1 for 10%).")
        print("       Skipping map image generation.")
        print("-" * 30)
        return 
    except Exception as e:
        print(f"ERROR: An unexpected error occurred creating the map surface: {e}")
        print("       Skipping map image generation.")
        print("-" * 30)
        return

    # --- Helper Drawing Functions (scaled) ---
    def scale_point(p):
        return (int(p[0] * MAP_SCALE_FACTOR), int(p[1] * MAP_SCALE_FACTOR))

    def scale_poly(poly_points):
        return [scale_point(p) for p in poly_points]

    def scale_value(v):
        scaled = int(v * MAP_SCALE_FACTOR)
        return max(1, scaled) # Ensure thickness/radius is at least 1 pixel

    # --- Draw onto the surface ---
    print("Drawing map elements...")
    world_surface.fill(GRASS_COLOR_BASE)

    # Rivers (Draw first using centerline)
    river_data_dict = world_elements.get("rivers", {})
    centerline_path = river_data_dict.get("centerline_path", [])
    if centerline_path and len(centerline_path) >= 2:
        scaled_centerline = [scale_point(p) for p in centerline_path]
        map_river_width_scaled = scale_value(MAP_RIVER_WIDTH) # Use dedicated map river width
        try: 
            pygame.draw.lines(world_surface, MAP_RIVER_COLOR, False, scaled_centerline, map_river_width_scaled)
        except Exception as e: 
            print(f"Warning: Error drawing river centerline on map image: {e}")


    # Forest Zone
    forest_zone = world_elements.get("forest_zone")
    if forest_zone and forest_zone.polygon_points:
        try: 
            pygame.draw.polygon(world_surface, forest_zone.ground_color, scale_poly(forest_zone.polygon_points))
        except Exception as e: 
            print(f"Warning: Error drawing forest polygon on map: {e}")

    # Kingdom Zone
    kingdom_zone = world_elements.get("kingdom_zone")
    if kingdom_zone and kingdom_zone.polygon_points:
        try: 
            pygame.draw.polygon(world_surface, kingdom_zone.ground_color, scale_poly(kingdom_zone.polygon_points))
        except Exception as e: 
            print(f"Warning: Error drawing kingdom polygon on map: {e}")

    # Path
    path_info = world_elements.get("path_info")
    if path_info and "start" in path_info and "end" in path_info and "width" in path_info:
        try:
            start_scaled = scale_point(path_info["start"])
            end_scaled = scale_point(path_info["end"])
            width_scaled = scale_value(path_info["width"]) # Path width on map can use its own constant if needed
            pygame.draw.line(world_surface, PATH_COLOR, start_scaled, end_scaled, width_scaled) # Use MAP_PATH_COLOR
        except Exception as e: print(f"Warning: Error drawing path on map: {e}")

    # Towers
    towers = world_elements.get("wall_towers", [])
    if towers:
        # Tower_size is for base rect; for map, use a smaller representation or a dedicated map constant
        tower_radius_map = max(1, scale_value(world_struct_stable.TOWER_SIZE * 0.15)) 
        for tower in towers:
            if 'base_rect' in tower:
                 center_pos_scaled = scale_point(tower['base_rect'].center)
                 pygame.draw.circle(world_surface, MAP_TOWER_COLOR, center_pos_scaled, tower_radius_map)

    # Gatehouse(s)
    gatehouses = world_elements.get("gatehouses", [])
    if gatehouses:
        gate_size_map = max(2, scale_value(world_struct_stable.GATEHOUSE_SIZE * 0.2)) 
        for gh in gatehouses:
             if 'base_rect' in gh:
                 center_pos_scaled = scale_point(gh['base_rect'].center)
                 gh_rect_map = pygame.Rect(0, 0, gate_size_map, gate_size_map)
                 gh_rect_map.center = center_pos_scaled
                 pygame.draw.rect(world_surface, MAP_GATEHOUSE_COLOR, gh_rect_map)

    # --- Split and Save the image ---
    print("Splitting and saving map image into two parts...")
    try:
        mid_x = scaled_width // 2
        width_part1 = mid_x
        width_part2 = scaled_width - mid_x 

        if width_part1 <= 0 or width_part2 <= 0 or scaled_height <= 0:
             print(f"ERROR: Invalid dimensions for splitting ({width_part1}x{scaled_height}, {width_part2}x{scaled_height}). Skipping save.")
             raise ValueError("Invalid dimensions for splitting map image") 

        print(f"Creating part 1 sub-surface (0, 0, {width_part1}, {scaled_height})")
        left_surface = world_surface.subsurface(pygame.Rect(0, 0, width_part1, scaled_height))

        print(f"Creating part 2 sub-surface ({mid_x}, 0, {width_part2}, {scaled_height})")
        right_surface = world_surface.subsurface(pygame.Rect(mid_x, 0, width_part2, scaled_height))

        base_name, extension = os.path.splitext(MAP_OUTPUT_FILENAME)
        if not extension: extension = ".png" 
        filename_part1 = f"{base_name}_part1{extension}"
        filename_part2 = f"{base_name}_part2{extension}"

        current_dir = os.path.dirname(__file__)
        project_root_dir = os.path.dirname(current_dir) # Assumes loading.py is in a subdirectory of project root
        save_path_part1 = os.path.join(project_root_dir, filename_part1)
        save_path_part2 = os.path.join(project_root_dir, filename_part2)

        print(f"Saving map part 1 to '{os.path.abspath(save_path_part1)}'...")
        try:
            pygame.image.save(left_surface, save_path_part1)
            print("SUCCESS: World map image part 1 saved.")
        except pygame.error as e:
            print(f"ERROR: Failed to save map image part 1: {e}")
        except Exception as e:
            print(f"ERROR: An unexpected error occurred during map image part 1 saving: {e}")

        print(f"Saving map part 2 to '{os.path.abspath(save_path_part2)}'...")
        try:
            pygame.image.save(right_surface, save_path_part2)
            print("SUCCESS: World map image part 2 saved.")
        except pygame.error as e:
            print(f"ERROR: Failed to save map image part 2: {e}")
        except Exception as e:
            print(f"ERROR: An unexpected error occurred during map image part 2 saving: {e}")

    except ValueError as ve: 
        print(f"ERROR: {ve}")
    except pygame.error as e:
        print(f"ERROR: A Pygame error occurred during map splitting/saving: {e}")
    except Exception as e:
        print(f"ERROR: An unexpected error occurred during map image splitting/saving: {e}")

    print("-" * 30)


TOTAL_LOADING_STEPS = 17 # Keep track of loading steps

def draw_loading_progress(surface, current_step, total_steps, message="Loading..."):
    """Draws the loading screen with progress bar and text."""
    screen_width = surface.get_width()
    screen_height = surface.get_height()

    # --- Clear Screen ---
    surface.fill((20, 20, 40)) # Dark blue background

    # --- Progress Bar ---
    bar_width = screen_width * 0.6
    bar_height = 30
    bar_x = (screen_width - bar_width) / 2
    bar_y = screen_height * 0.6
    bar_bg_color = (60, 60, 80)
    bar_fg_color = (100, 180, 255)

    # Calculate progress
    progress = 0.0
    if total_steps > 0:
        progress = min(1.0, max(0.0, current_step / total_steps))

    # Draw background bar
    pygame.draw.rect(surface, bar_bg_color, (bar_x, bar_y, bar_width, bar_height))
    # Draw foreground bar
    fg_width = bar_width * progress
    pygame.draw.rect(surface, bar_fg_color, (bar_x, bar_y, fg_width, bar_height))
    # Draw border
    pygame.draw.rect(surface, (200, 200, 220), (bar_x, bar_y, bar_width, bar_height), 2)

    # --- Text ---
    font = None
    try:
        # Use a slightly larger font for loading text
        font = pygame.font.SysFont(None, 36)
    except Exception as e:
        print(f"Could not load font for loading screen: {e}")
        # Font failed, can't draw text

    if font:
        # Loading Message
        text_surf = font.render(message, True, (220, 220, 240))
        text_rect = text_surf.get_rect(center=(screen_width / 2, screen_height * 0.5))
        surface.blit(text_surf, text_rect)

        # Percentage Text
        percent_text = f"{int(progress * 100)}%"
        percent_surf = font.render(percent_text, True, (220, 220, 240))
        percent_rect = percent_surf.get_rect(center=(screen_width / 2, bar_y + bar_height / 2))
        surface.blit(percent_surf, percent_rect)

    # --- Update Display ---
    pygame.display.flip()

    # --- Keep Window Responsive ---
    pygame.event.pump() # Process internal events


def run_loading_screen(surface, game_state, mixer_initialized):
    """
    Handles the loading process and updates the loading screen.
    Returns the loaded world_data, collision_quadtree, effective dimensions,
    loaded player animations, enemy animations, and initialized managers.
    """

    # Define variables to store loaded data
    world_data = None
    collision_quadtree = None
    effective_world_width = 0
    effective_world_height = 0
    player_idle_frames, player_walk_frames, player_attack_frames, player_hurt_frames, player_death_frames = [None]*5
    player_frame_dims = None
    all_enemy_animations = {}
    combat_manager = None
    npc_manager = None

    current_step = 0
    draw_loading_progress(surface, current_step, TOTAL_LOADING_STEPS, "Initializing...")
    pygame.time.wait(100) # Small pause to ensure first draw

    # --- Step 1 & 2: World Loading/Generation ---
    print("Loading Step: World Data...")
    # world_data includes zone objects, river dict (tile_pos, centerline_path), etc.
    # collision_quadtree is created but not populated yet here
    world_data, collision_quadtree = world_struct_stable.load_or_generate_world()

    # load_all_sprites is now called inside load_or_generate_world and result stored in world_data["loaded_sprites"]
    # So, no need to call it again here.
    # loaded_sprites_for_world = load_all_sprites() # asset.assets.load_all_sprites()
    # world_data["loaded_sprites"] = loaded_sprites_for_world

    current_step += 2 # Count as 2 steps (load/gen + sprite loading inside world_struct)
    draw_loading_progress(surface, current_step, TOTAL_LOADING_STEPS, "World Generated...")
    pygame.time.wait(50)

    # --- Step 3-7: Player Animations ---
    print("Loading Step: Player Animations...")
    player_idle_frames, player_frame_dims = load_sprite_sheet(SPRITE_SHEET_PLAYER_IDLE_FILENAME, NUM_PLAYER_IDLE_FRAMES)
    current_step += 1; draw_loading_progress(surface, current_step, TOTAL_LOADING_STEPS, "Loading Player...")
    player_walk_frames, _ = load_sprite_sheet(SPRITE_SHEET_PLAYER_WALK_FILENAME, NUM_PLAYER_WALK_FRAMES)
    current_step += 1; draw_loading_progress(surface, current_step, TOTAL_LOADING_STEPS, "Loading Player...")
    player_attack_frames, _ = load_sprite_sheet(SPRITE_SHEET_PLAYER_ATTACK_FILENAME, NUM_PLAYER_ATTACK_FRAMES)
    current_step += 1; draw_loading_progress(surface, current_step, TOTAL_LOADING_STEPS, "Loading Player...")
    player_hurt_frames, _ = load_sprite_sheet(SPRITE_SHEET_PLAYER_HURT_FILENAME, NUM_PLAYER_HURT_FRAMES)
    current_step += 1; draw_loading_progress(surface, current_step, TOTAL_LOADING_STEPS, "Loading Player...")
    player_death_frames, _ = load_sprite_sheet(SPRITE_SHEET_PLAYER_DEATH_FILENAME, NUM_PLAYER_DEATH_FRAMES)
    current_step += 1; draw_loading_progress(surface, current_step, TOTAL_LOADING_STEPS, "Player Assets Loaded...")
    pygame.time.wait(50)

    if not player_idle_frames or not player_frame_dims:
        print("FATAL: Failed to load essential player idle frames during loading screen. Exiting.")
        pygame.quit(); sys.exit()
    player_animations = {
        'idle': player_idle_frames, 'walk': player_walk_frames, 'attack': player_attack_frames,
        'hurt': player_hurt_frames, 'death': player_death_frames, 'dims': player_frame_dims
    }

    # --- Step 8-12: Enemy Animations (Orc Example) ---
    print("Loading Step: Enemy Animations...")
    orc_idle_frames, orc_frame_dims = load_sprite_sheet(SPRITE_SHEET_ORC_IDLE_FILENAME, NUM_ORC_IDLE_FRAMES)
    current_step += 1; draw_loading_progress(surface, current_step, TOTAL_LOADING_STEPS, "Loading Enemies...")
    orc_walk_frames, _ = load_sprite_sheet(SPRITE_SHEET_ORC_WALK_FILENAME, NUM_ORC_WALK_FRAMES)
    current_step += 1; draw_loading_progress(surface, current_step, TOTAL_LOADING_STEPS, "Loading Enemies...")
    orc_attack_frames, _ = load_sprite_sheet(SPRITE_SHEET_ORC_ATTACK_FILENAME, NUM_ORC_ATTACK_FRAMES)
    current_step += 1; draw_loading_progress(surface, current_step, TOTAL_LOADING_STEPS, "Loading Enemies...")
    orc_hurt_frames, _ = load_sprite_sheet(SPRITE_SHEET_ORC_HURT_FILENAME, NUM_ORC_HURT_FRAMES)
    current_step += 1; draw_loading_progress(surface, current_step, TOTAL_LOADING_STEPS, "Loading Enemies...")
    orc_death_frames, _ = load_sprite_sheet(SPRITE_SHEET_ORC_DEATH_FILENAME, NUM_ORC_DEATH_FRAMES)
    current_step += 1; draw_loading_progress(surface, current_step, TOTAL_LOADING_STEPS, "Enemy Assets Loaded...")
    pygame.time.wait(50)

    if all([orc_idle_frames, orc_walk_frames, orc_attack_frames, orc_hurt_frames, orc_death_frames, orc_frame_dims]):
        all_enemy_animations["Sword_Orc"] = {
            'idle': orc_idle_frames, 'walk': orc_walk_frames, 'attack': orc_attack_frames,
            'hurt': orc_hurt_frames, 'death': orc_death_frames, 'dims': orc_frame_dims
        }
    else:
        print("WARNING: Failed to load one or more Orc animations.")

    # --- Step 13: Load Music ---
    print("Loading Step: Music...")
    if mixer_initialized:
        try:
            pygame.mixer.music.load(MUSIC_FILE_PATH)
            pygame.mixer.music.set_volume(MUSIC_VOLUME)
        except pygame.error as e:
            print(f"Error loading music file during loading screen: {e}")
    current_step += 1; draw_loading_progress(surface, current_step, TOTAL_LOADING_STEPS, "Audio Loaded...")
    pygame.time.wait(50)

    # --- Step 14: Determine World Size & Populate Quadtree ---
    print("Loading Step: Quadtree Population...")
    if game_state == "dungeon":
        dungeon_world_width = world_struct_stable.DUNGEON_GRID_WIDTH * world_struct_stable.DUNGEON_TILE_SIZE
        dungeon_world_height = world_struct_stable.DUNGEON_GRID_HEIGHT * world_struct_stable.DUNGEON_TILE_SIZE
        dungeon_boundary_rect = pygame.Rect(0, 0, dungeon_world_width, dungeon_world_height)
        collision_quadtree.boundary = dungeon_boundary_rect # Update quadtree boundary
        world_struct_stable.populate_quadtree_with_dungeon(collision_quadtree, world_data["dungeon_grid"])
        effective_world_width = dungeon_world_width
        effective_world_height = dungeon_world_height
    elif game_state == "overworld":
        overworld_boundary_rect = pygame.Rect(0, 0, world_struct_stable.WORLD_WIDTH, world_struct_stable.WORLD_HEIGHT)
        collision_quadtree.boundary = overworld_boundary_rect # Update quadtree boundary
        world_struct_stable.populate_quadtree_with_overworld(collision_quadtree, world_data["colliders"])
        effective_world_width = world_struct_stable.WORLD_WIDTH
        effective_world_height = world_struct_stable.WORLD_HEIGHT
    else: 
        print(f"ERROR: Unknown game_state '{game_state}'. Defaulting to overworld bounds for quadtree.")
        overworld_boundary_rect = pygame.Rect(0, 0, world_struct_stable.WORLD_WIDTH, world_struct_stable.WORLD_HEIGHT)
        collision_quadtree.boundary = overworld_boundary_rect
        if "colliders" in world_data: # Ensure colliders exist before populating
             world_struct_stable.populate_quadtree_with_overworld(collision_quadtree, world_data["colliders"])
        else:
             print("Warning: No 'colliders' found in world_data for default quadtree population.")
        effective_world_width = world_struct_stable.WORLD_WIDTH
        effective_world_height = world_struct_stable.WORLD_HEIGHT
    current_step += 1; draw_loading_progress(surface, current_step, TOTAL_LOADING_STEPS, "Optimizing World...")
    pygame.time.wait(50)

    # --- Step 15 & 16: Initialize Managers ---
    print("Loading Step: Preparing Managers...")
    combat_manager = combat_mech_stable.CombatManager(world_data, collision_quadtree, world_struct_stable.is_point_in_polygon, all_enemy_animations, network.network_players)
    npc_manager = npc_system_stable.NPCManager(world_data, world_struct_stable.SCREEN_HEIGHT, world_struct_stable.SCREEN_WIDTH, network.network_players, network.is_host)
    current_step += 2; draw_loading_progress(surface, current_step, TOTAL_LOADING_STEPS, "Preparing Inhabitants...")
    pygame.time.wait(50)

    # --- Step 17: Finalization & Map Image Generation ---
    should_generate_map_image = False 
    while True:
        pygame.event.pump()
        print("\n" + "="*30)
        generate_choice = input(" Generate and save world map image (yes/no)? ").lower().strip()
        print("="*30 + "\n")
        if generate_choice == 'yes':
            should_generate_map_image = True
            break
        elif generate_choice == 'no':
            should_generate_map_image = False
            break
        else:
            print(" > Invalid input. Please enter 'yes' or 'no'.")
            pygame.time.wait(50) 

    print("Loading Step: Finalization...") 

    if should_generate_map_image:
        print("   - Generating Map Image (User Request)...")
        draw_loading_progress(surface, current_step, TOTAL_LOADING_STEPS, "Generating Map...") 
        pygame.time.wait(50) 
        generate_and_save_world_map_image(
            world_data,
            world_struct_stable.WORLD_WIDTH, 
            world_struct_stable.WORLD_HEIGHT
        )
    else:
        print("   - Skipping Map Image Generation (User Request).")

    current_step += 1
    draw_loading_progress(surface, current_step, TOTAL_LOADING_STEPS, "Ready!")
    pygame.time.wait(500) 


    return (world_data, collision_quadtree,
            effective_world_width, effective_world_height,
            all_enemy_animations, player_animations,
            combat_manager, npc_manager)