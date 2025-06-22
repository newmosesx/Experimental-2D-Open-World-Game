import pygame
import random # Needed for wall sprite choice if not done in generation
import math # Needed potentially if angles used directly (though generate_wall_tile_data handles it)
from .world_constants import * # Import all constants needed for drawing
from .utils import apply_camera_to_point, apply_camera_to_rect # Import camera utils

def draw_world_background(screen, camera_x, camera_y, world_elements, game_state):
    """Draws the base background (grass, zones, paths or dungeon tiles), then rivers."""
    screen_rect_for_culling = screen.get_rect()
    camera_world_rect = pygame.Rect(camera_x, camera_y, SCREEN_WIDTH, SCREEN_HEIGHT) # Define for overworld culling
    loaded_sprites = world_elements.get("loaded_sprites", {}) # Get loaded sprites once


    if game_state == "dungeon":
        # --- Dungeon Drawing --- (Keep as is)
        dungeon_grid = world_elements.get("dungeon_grid")
        if not dungeon_grid: return
        start_col = max(0, int(camera_x // DUNGEON_TILE_SIZE)); end_col = min(DUNGEON_GRID_WIDTH, int((camera_x + SCREEN_WIDTH) // DUNGEON_TILE_SIZE) + 1)
        start_row = max(0, int(camera_y // DUNGEON_TILE_SIZE)); end_row = min(DUNGEON_GRID_HEIGHT, int((camera_y + SCREEN_HEIGHT) // DUNGEON_TILE_SIZE) + 1)
        for y in range(start_row, end_row):
            for x in range(start_col, end_col):
                if 0 <= y < len(dungeon_grid) and 0 <= x < len(dungeon_grid[y]):
                    tile_type = dungeon_grid[y][x]
                    world_tile_x = x * DUNGEON_TILE_SIZE; world_tile_y = y * DUNGEON_TILE_SIZE
                    tile_screen_x, tile_screen_y = apply_camera_to_point(world_tile_x, world_tile_y, camera_x, camera_y)
                    if tile_screen_x < SCREEN_WIDTH and tile_screen_x + DUNGEON_TILE_SIZE > 0 and tile_screen_y < SCREEN_HEIGHT and tile_screen_y + DUNGEON_TILE_SIZE > 0:
                        tile_rect_screen = pygame.Rect(tile_screen_x, tile_screen_y, DUNGEON_TILE_SIZE, DUNGEON_TILE_SIZE)
                        if tile_type == TILE_WALL: pygame.draw.rect(screen, DUNGEON_COLOR_WALL, tile_rect_screen)
                        elif tile_type == TILE_FLOOR: pygame.draw.rect(screen, DUNGEON_COLOR_FLOOR, tile_rect_screen)

    elif game_state == "overworld":
        # --- Overworld Drawing ---
        screen.fill(GRASS_COLOR_BASE) # Fill entire background first
        
        forest_zone = world_elements.get("forest_zone")
        kingdom_zone = world_elements.get("kingdom_zone")

        # --- Draw Zone Ground Colors FIRST ---
        # Draw Forest Ground
        if forest_zone and forest_zone.polygon_points:
            forest_poly_screen = [apply_camera_to_point(p[0], p[1], camera_x, camera_y) for p in forest_zone.polygon_points]
            if len(forest_poly_screen) > 2: # Ensure it's a polygon
                # Basic culling for the polygon based on its screen bounding box
                # More precise culling would involve checking if the screen rect intersects the polygon itself.
                min_x_s = min(p[0] for p in forest_poly_screen); max_x_s = max(p[0] for p in forest_poly_screen)
                min_y_s = min(p[1] for p in forest_poly_screen); max_y_s = max(p[1] for p in forest_poly_screen)
                poly_screen_bbox = pygame.Rect(min_x_s, min_y_s, max_x_s - min_x_s, max_y_s - min_y_s)
                if screen_rect_for_culling.colliderect(poly_screen_bbox):
                    pygame.draw.polygon(screen, forest_zone.ground_color, forest_poly_screen)

        # Draw Kingdom Ground
        if kingdom_zone and kingdom_zone.polygon_points:
            kingdom_poly_screen = [apply_camera_to_point(p[0], p[1], camera_x, camera_y) for p in kingdom_zone.polygon_points]
            if len(kingdom_poly_screen) > 2:
                min_x_s = min(p[0] for p in kingdom_poly_screen); max_x_s = max(p[0] for p in kingdom_poly_screen)
                min_y_s = min(p[1] for p in kingdom_poly_screen); max_y_s = max(p[1] for p in kingdom_poly_screen)
                poly_screen_bbox = pygame.Rect(min_x_s, min_y_s, max_x_s - min_x_s, max_y_s - min_y_s)
                if screen_rect_for_culling.colliderect(poly_screen_bbox):
                    pygame.draw.polygon(screen, kingdom_zone.ground_color, kingdom_poly_screen)

        # Draw Path (Draw before rivers so river can flow over path if desired, or swap order)
        path_info = world_elements.get("path_info")
        if path_info:
            path_start_screen = apply_camera_to_point(*path_info["start"], camera_x, camera_y); path_end_screen = apply_camera_to_point(*path_info["end"], camera_x, camera_y)
            path_clip = screen_rect_for_culling.clipline(path_start_screen, path_end_screen)
            # Ensure width is at least 1 pixel for drawing
            draw_width = max(1, path_info.get("width", 1))
            if path_clip: pygame.draw.line(screen, path_info["color"], path_clip[0], path_clip[1], draw_width)


        # --- Draw River Tiles (using loaded texture) ---
        river_data_dict = world_elements.get("rivers", {}) # Expecting a dict now
        river_tile_positions = river_data_dict.get("tile_positions", [])
        water_sprite_info = loaded_sprites.get('water_texture') 

        if water_sprite_info and river_tile_positions:
            water_tile_surface = water_sprite_info.get('surface')
            tile_w = water_sprite_info.get('width', 0) 
            tile_h = water_sprite_info.get('height', 0)

            if water_tile_surface and tile_w > 0 and tile_h > 0:
                for tx, ty in river_tile_positions:
                    tile_world_rect = pygame.Rect(tx, ty, tile_w, tile_h)
                    if camera_world_rect.colliderect(tile_world_rect):
                        screen_x, screen_y = apply_camera_to_point(tx, ty, camera_x, camera_y)
                        tile_screen_rect = pygame.Rect(screen_x, screen_y, tile_w, tile_h)
                        if screen_rect_for_culling.colliderect(tile_screen_rect):
                            screen.blit(water_tile_surface, (screen_x, screen_y))


def draw_world_details(screen, camera_x, camera_y, world_elements, game_state):
    """Draws details like grass and trees (sorted)."""
    if game_state == "overworld":
        camera_world_rect = pygame.Rect(camera_x, camera_y, SCREEN_WIDTH, SCREEN_HEIGHT)
        screen_rect_for_culling = screen.get_rect()
        loaded_sprites = world_elements.get("loaded_sprites", {}) # Get loaded sprites dict

        # Draw Grass Details
        grass_details = world_elements.get("grass_details", [])
        for detail in grass_details:
             # Check if detail rect exists and is valid
            if 'rect' in detail and isinstance(detail['rect'], pygame.Rect):
                if camera_world_rect.colliderect(detail['rect']):
                    detail_screen_rect = apply_camera_to_rect(detail['rect'], camera_x, camera_y)
                    # Check if the transformed rect is still on screen
                    if screen_rect_for_culling.colliderect(detail_screen_rect):
                         # Ensure color exists and is valid
                         color = detail.get('color', (0, 255, 0)) # Default to green if missing
                         pygame.draw.rect(screen, color, detail_screen_rect)

        # Draw Forest Trees (Sorted)
        forest_trees = world_elements.get("forest_trees", [])
        tree_sprite_info = loaded_sprites.get('tree')

        if tree_sprite_info and forest_trees: # Only proceed if sprite and trees exist
            # Sort trees by the bottom of their collider for correct draw order
            forest_trees_sorted = sorted(forest_trees, key=lambda t: t['collider'].bottom)
            tree_sprite = tree_sprite_info.get('surface')
            sprite_w = tree_sprite_info.get('width', 0)
            sprite_h = tree_sprite_info.get('height', 0)

            if tree_sprite and sprite_w > 0 and sprite_h > 0: # Check validity
                for tree in forest_trees_sorted:
                    collider_rect = tree['collider']
                    # Anchor sprite drawing based on the bottom-center of the collider
                    anchor_world_x = collider_rect.centerx
                    anchor_world_y = collider_rect.bottom
                    # Calculate top-left corner for blitting
                    sprite_world_draw_x = anchor_world_x - sprite_w // 2
                    sprite_world_draw_y = anchor_world_y - sprite_h # Draw sprite above the anchor y
                    # Bounding box for the visual sprite (used for culling)
                    sprite_world_bbox = pygame.Rect(sprite_world_draw_x, sprite_world_draw_y, sprite_w, sprite_h)

                    # Culling: Check if the sprite's bounding box is within the camera view
                    if camera_world_rect.colliderect(sprite_world_bbox):
                        # Convert world draw coordinates to screen coordinates
                        draw_screen_x, draw_screen_y = apply_camera_to_point(sprite_world_draw_x, sprite_world_draw_y, camera_x, camera_y)
                        # Final Culling: Check if the sprite is actually visible on the screen surface
                        sprite_screen_rect = pygame.Rect(draw_screen_x, draw_screen_y, sprite_w, sprite_h)
                        if screen_rect_for_culling.colliderect(sprite_screen_rect):
                            screen.blit(tree_sprite, (draw_screen_x, draw_screen_y))


def draw_kingdom_structures(screen, camera_x, camera_y, world_elements):
    """Draws kingdom walls (ROTATED tiles), towers, gatehouses, and buildings, sorted by Y."""
    camera_world_rect = pygame.Rect(camera_x, camera_y, SCREEN_WIDTH, SCREEN_HEIGHT)
    screen_rect_for_culling = screen.get_rect()

    wall_tiles = world_elements.get("wall_tiles", []) # List of {'pos': (cx,cy), 'angle': a, 'sprite_key': k}
    kingdom_structures = world_elements.get("kingdom_structures", []) # List of {'base_rect': r} (Buildings)
    wall_towers = world_elements.get("wall_towers", [])         # List of {'base_rect': r}
    gatehouses = world_elements.get("gatehouses", [])           # List of {'base_rect': r}
    loaded_sprites = world_elements.get("loaded_sprites", {})

    drawable_items = [] # Combine all kingdom elements for Y-sorting

    # --- 1. Add Wall Tiles to Sort List ---
    wall_sprite_front_info = loaded_sprites.get('wall_front') 
    wall_sprite_back_info = loaded_sprites.get('wall_back')
    wall_surfaces = {}
    if wall_sprite_front_info:
        wall_surfaces['wall_front'] = wall_sprite_front_info
    if wall_sprite_back_info:
        wall_surfaces['wall_back'] = wall_sprite_back_info

    for tile_data in wall_tiles:
        sprite_key = tile_data.get('sprite_key')
        sprite_info = wall_surfaces.get(sprite_key) 
        pos = tile_data.get('pos')
        if sprite_info and pos: 
            drawable_items.append({
                'type': 'wall_tile',
                'data': tile_data,          
                'sprite_info': sprite_info, 
                'y_sort': pos[1] 
            })

    # --- 2. Add Gatehouses to Sort List ---
    gatehouse_sprite_info = loaded_sprites.get('gatehouse')
    if gatehouse_sprite_info:
        for gh in gatehouses: 
            base_rect = gh.get('base_rect')
            if base_rect:
                drawable_items.append({
                    'type': 'gatehouse',
                    'data': gh, 
                    'sprite_info': gatehouse_sprite_info,
                    'y_sort': base_rect.bottom 
                })

    # --- 3. Add Wall Towers to Sort List ---
    tower_sprite_info = loaded_sprites.get('tower')
    if tower_sprite_info:
        for tower in wall_towers:
            base_rect = tower.get('base_rect')
            if base_rect:
                 drawable_items.append({
                    'type': 'tower',
                    'data': tower, 
                    'sprite_info': tower_sprite_info,
                    'y_sort': base_rect.bottom 
                })

    # --- 4. Add Buildings to Sort List ---
    building_sprite_info = loaded_sprites.get('building')
    if building_sprite_info:
        for structure in kingdom_structures:
            base_rect = structure.get('base_rect')
            if base_rect:
                 drawable_items.append({
                    'type': 'building',
                    'data': structure, 
                    'sprite_info': building_sprite_info,
                    'y_sort': base_rect.bottom 
                })

    # --- 5. Sort all items by Y-coordinate ---
    drawable_items.sort(key=lambda x: x['y_sort'])

    # --- 6. Draw Sorted Items ---
    for item in drawable_items:
        item_type = item.get('type')
        item_data = item.get('data')
        sprite_info = item.get('sprite_info')

        if not item_type or not item_data or not sprite_info:
            continue

        base_sprite_surface = sprite_info.get('surface')
        if not base_sprite_surface: 
             continue


        if item_type == 'wall_tile':
            pos = item_data.get('pos')
            angle = item_data.get('angle', 0) 

            if not pos: continue 

            world_center_x, world_center_y = pos

            try:
                rotated_surface = pygame.transform.rotate(base_sprite_surface, angle)
            except pygame.error as e:
                print(f"Error rotating wall tile: {e}. Skipping tile.")
                continue

            rotated_rect = rotated_surface.get_rect(center=(world_center_x, world_center_y))
            sprite_world_bbox = rotated_rect
            draw_world_x = rotated_rect.left
            draw_world_y = rotated_rect.top
            surface_to_blit = rotated_surface

        else: # Buildings, Towers, Gatehouses (no rotation needed here)
            base_rect = item_data.get('base_rect')
            sprite_w = sprite_info.get('width', 0)
            sprite_h = sprite_info.get('height', 0)

            if not base_rect or sprite_w <= 0 or sprite_h <= 0:
                 continue

            anchor_world_x = base_rect.centerx
            anchor_world_y = base_rect.bottom
            draw_world_x = anchor_world_x - sprite_w // 2
            draw_world_y = anchor_world_y - sprite_h
            sprite_world_bbox = pygame.Rect(draw_world_x, draw_world_y, sprite_w, sprite_h)
            surface_to_blit = base_sprite_surface 

        # Common drawing logic (culling and blitting)
        if camera_world_rect.colliderect(sprite_world_bbox):
            draw_screen_x, draw_screen_y = apply_camera_to_point(draw_world_x, draw_world_y, camera_x, camera_y)
            blit_rect_screen = surface_to_blit.get_rect(topleft=(draw_screen_x, draw_screen_y))
            if screen_rect_for_culling.colliderect(blit_rect_screen):
                screen.blit(surface_to_blit, blit_rect_screen.topleft)