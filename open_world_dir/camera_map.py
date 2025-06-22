import pygame
import threading
import world_struct as world_struct_stable # Need WORLD_WIDTH/HEIGHT
# <<< NETWORK: Import player module for type hinting and ID check >>>
import enemies.player as player_module
# <<< NETWORK: Import network config for local player ID >>>
import NETconfig

# --- Camera State ---
camera_x = 0
camera_y = 0

# --- Map State & Constants ---
# show_map = False # This internal 'show_map' is no longer the primary controller from open_world.
MAP_WIDTH = world_struct_stable.MAP_WIDTH 
MAP_HEIGHT = world_struct_stable.MAP_HEIGHT
MAP_X = world_struct_stable.MAP_X
MAP_Y = world_struct_stable.MAP_Y
MAP_BG_COLOR = world_struct_stable.MAP_BG_COLOR
MAP_BORDER_COLOR = world_struct_stable.MAP_BORDER_COLOR
MAP_PLAYER_COLOR = world_struct_stable.MAP_PLAYER_COLOR
MAP_OTHER_PLAYER_COLOR = (0, 0, 255) 
MAP_PLAYER_SIZE = world_struct_stable.MAP_PLAYER_SIZE
MAP_ZONE_FOREST_COLOR = world_struct_stable.MAP_ZONE_FOREST_COLOR
MAP_ZONE_KINGDOM_COLOR = world_struct_stable.MAP_ZONE_KINGDOM_COLOR
MAP_WALL_COLOR = (80, 80, 80, 200) 
MAP_PATH_COLOR = world_struct_stable.MAP_PATH_COLOR
MAP_TOWER_COLOR = world_struct_stable.MAP_TOWER_COLOR
MAP_RIVER_COLOR = world_struct_stable.MAP_RIVER_COLOR 
MAP_RIVER_WIDTH = world_struct_stable.MAP_RIVER_WIDTH 


# --- Map Surface (Create once) ---
map_surface = pygame.Surface((MAP_WIDTH, MAP_HEIGHT), pygame.SRCALPHA) 

# --- Helper Functions ---
def apply_camera_to_point(world_x, world_y): 
    """Converts world coordinates to screen coordinates based on global camera_x, camera_y."""
    return int(world_x - camera_x), int(world_y - camera_y)

def get_camera_world_rect():
    """Returns a pygame.Rect representing the camera's view in world coordinates."""
    return pygame.Rect(camera_x, camera_y, world_struct_stable.SCREEN_WIDTH, world_struct_stable.SCREEN_HEIGHT)

def update_camera(player_x, player_y, effective_world_width, effective_world_height):
    """Updates the camera position to follow the player, clamping to world bounds."""
    global camera_x, camera_y
    target_camera_x = player_x - world_struct_stable.SCREEN_WIDTH // 2
    target_camera_y = player_y - world_struct_stable.SCREEN_HEIGHT // 2

    camera_x = max(0, min(target_camera_x, effective_world_width - world_struct_stable.SCREEN_WIDTH))
    camera_y = max(0, min(target_camera_y, effective_world_height - world_struct_stable.SCREEN_HEIGHT))

# def toggle_map(): # This function is no longer used by open_world.py for controlling visibility
#     """Toggles the map visibility."""
#     global show_map
#     show_map = not show_map

# --- Map Drawing Function ---
def world_to_map_coords(world_x, world_y, world_width, world_height):
    """Converts world coordinates to map coordinates."""
    map_rel_x = 0.0
    if world_width > 0: 
         map_rel_x = max(0.0, min((world_x / world_width) * MAP_WIDTH, MAP_WIDTH - 1.0))
    map_rel_y = 0.0
    if world_height > 0: 
        map_rel_y = max(0.0, min((world_y / world_height) * MAP_HEIGHT, MAP_HEIGHT - 1.0))
    return int(map_rel_x), int(map_rel_y)

def draw_map_overlay(surface, local_player, world_data, world_width, world_height, game_state, network_players_list):
    """Draws the mini-map overlay onto the main surface, showing all players."""
    # REMOVED: if not show_map: return 
    # The decision to call this function is now handled by open_world.py based on its own 'show_map'

    w_to_map = lambda x, y: world_to_map_coords(x, y, world_width, world_height)

    map_surface.fill(MAP_BG_COLOR)

    if game_state == "overworld":
        forest_zone = world_data.get("forest_zone")
        if forest_zone and forest_zone.polygon_points:
            map_forest_boundary = [w_to_map(p[0], p[1]) for p in forest_zone.polygon_points]
            if len(map_forest_boundary) > 2:
                pygame.draw.polygon(map_surface, MAP_ZONE_FOREST_COLOR, map_forest_boundary)
        
        kingdom_zone = world_data.get("kingdom_zone")
        if kingdom_zone and kingdom_zone.polygon_points:
            map_kingdom_boundary = [w_to_map(p[0], p[1]) for p in kingdom_zone.polygon_points]
            if len(map_kingdom_boundary) > 2:
                pygame.draw.polygon(map_surface, MAP_ZONE_KINGDOM_COLOR, map_kingdom_boundary)
        
        path_info = world_data.get("path_info")
        if path_info and "start" in path_info and "end" in path_info:
            map_path_start = w_to_map(*path_info["start"]); map_path_end = w_to_map(*path_info["end"])
            # Use a defined constant or a small fixed value for path width on map
            map_path_line_width = max(1, int(MAP_RIVER_WIDTH / 2)) # Example: half of river width, min 1
            if world_struct_stable.MAP_PATH_COLOR: # Ensure MAP_PATH_COLOR is defined
                 pygame.draw.line(map_surface, world_struct_stable.MAP_PATH_COLOR, map_path_start, map_path_end, map_path_line_width) 

        kingdom_wall_vertices = world_data.get("kingdom_wall_vertices") 
        if kingdom_wall_vertices:
            map_wall_verts = [w_to_map(v[0], v[1]) for v in kingdom_wall_vertices]
            map_wall_verts_count = len(map_wall_verts)
            gate_info = world_data.get("gate_info", {}); gate_segment_index = gate_info.get("segment_index", -1)
            for i in range(map_wall_verts_count):
                if i != gate_segment_index or not (gate_info.get("p1") and gate_info.get("p2")):
                    pygame.draw.line(map_surface, MAP_WALL_COLOR, map_wall_verts[i], map_wall_verts[(i + 1) % map_wall_verts_count], 1)
        
        for structure_key in ["wall_towers", "gatehouses"]:
             if structure_key in world_data:
                 for item in world_data[structure_key]:
                     if 'base_rect' in item:
                         map_pos = w_to_map(item['base_rect'].centerx, item['base_rect'].centery)
                         pygame.draw.rect(map_surface, MAP_TOWER_COLOR, (map_pos[0]-1, map_pos[1]-1, 3, 3)) 

        river_data_dict = world_data.get("rivers", {})
        centerline_path = river_data_dict.get("centerline_path", [])
        if centerline_path and len(centerline_path) >= 2:
            map_centerline = [w_to_map(p[0], p[1]) for p in centerline_path]
            pygame.draw.lines(map_surface, MAP_RIVER_COLOR, False, map_centerline, MAP_RIVER_WIDTH)


    elif game_state == "dungeon":
         if "dungeon_grid" in world_data:
             grid = world_data["dungeon_grid"]
             tile_size_world = world_struct_stable.DUNGEON_TILE_SIZE
             map_tile_w = max(1, int((MAP_WIDTH / world_width) * tile_size_world)) if world_width > 0 else 1
             map_tile_h = max(1, int((MAP_HEIGHT / world_height) * tile_size_world)) if world_height > 0 else 1
             
             for r_idx, row in enumerate(grid):
                 for c_idx, tile_type in enumerate(row):
                     map_x, map_y = w_to_map(c_idx * tile_size_world, r_idx * tile_size_world)
                     tile_color_on_map = None
                     if tile_type == world_struct_stable.TILE_WALL:
                         tile_color_on_map = MAP_WALL_COLOR
                     elif tile_type == world_struct_stable.TILE_FLOOR:
                         # Use a slightly different color for dungeon floor on map to distinguish from path
                         tile_color_on_map = world_struct_stable.MAP_PATH_COLOR # Or a dedicated dungeon floor map color
                     
                     if tile_color_on_map:
                        pygame.draw.rect(map_surface, tile_color_on_map, (map_x, map_y, map_tile_w, map_tile_h))

    pygame.draw.rect(map_surface, MAP_BORDER_COLOR, map_surface.get_rect(), 1)

    local_player_id = NETconfig.my_player_id 
    # network_players_list is already a list of player objects passed from open_world.py
    for p_obj in network_players_list: 
        if p_obj: 
            if hasattr(p_obj, 'x') and hasattr(p_obj, 'y') and hasattr(p_obj, 'player_id'):
                map_player_x, map_player_y = w_to_map(p_obj.x, p_obj.y)
                player_map_color = MAP_PLAYER_COLOR if p_obj.player_id == local_player_id else MAP_OTHER_PLAYER_COLOR
                pygame.draw.circle(map_surface, player_map_color, (map_player_x, map_player_y), MAP_PLAYER_SIZE)

    surface.blit(map_surface, (MAP_X, MAP_Y))