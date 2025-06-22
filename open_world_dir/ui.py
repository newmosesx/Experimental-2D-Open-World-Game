import pygame

# Initialize UI font (needs pygame.font.init() called first)
ui_font = None
try:
    pygame.font.init() # Ensure font module is initialized
    ui_font = pygame.font.SysFont(None, 24) # Use a default system font
except Exception as e:
    print(f"Could not load UI font: {e}. UI text will not be drawn.")

def draw_ui(surface, player):
    """Draws the player's stats UI."""
    if not ui_font or player is None:
        return # Cannot draw if font failed or player doesn't exist

    y_offset = 10 # Starting y position for UI elements
    text_color = (255, 255, 255) # White text
    bg_color = (0, 0, 0, 150) # Semi-transparent black background

    # Health Bar (Optional visual bar)
    health_bar_width = 150
    health_bar_height = 15
    health_bar_x = 10
    health_bar_y = y_offset
    health_ratio = 0.0
    if player.max_health > 0:
        health_ratio = max(0.0, min(1.0, player.health / player.max_health))
    current_health_width = int(health_bar_width * health_ratio)
    # Draw background bar
    pygame.draw.rect(surface, (80, 0, 0, 150), (health_bar_x, health_bar_y, health_bar_width, health_bar_height))
    # Draw foreground health bar
    pygame.draw.rect(surface, (0, 200, 0, 200), (health_bar_x, health_bar_y, current_health_width, health_bar_height))
    # Draw border
    pygame.draw.rect(surface, (200, 200, 200, 200), (health_bar_x, health_bar_y, health_bar_width, health_bar_height), 1)
    y_offset += health_bar_height + 5 # Add padding below bar

    # Health Text (HP: xx / yy) - Render with background for readability
    health_text = f"HP: {int(round(player.health))} / {player.max_health}"
    health_surf = ui_font.render(health_text, True, text_color)
    # Create a slightly larger background surface
    bg_surf = pygame.Surface((health_surf.get_width() + 8, health_surf.get_height() + 4), pygame.SRCALPHA)
    bg_surf.fill(bg_color)
    bg_surf.blit(health_surf, (4, 2)) # Blit text onto background with padding
    health_rect = bg_surf.get_rect(topleft=(10, y_offset))
    surface.blit(bg_surf, health_rect)
    y_offset += health_rect.height + 2 # Add padding

    # Defense Text (DEF: xx%)
    def_perc = player.defense * 100
    def_text = f"DEF: {def_perc:.0f}%"
    def_surf = ui_font.render(def_text, True, (200, 200, 255)) # Lighter blue
    bg_surf_def = pygame.Surface((def_surf.get_width() + 8, def_surf.get_height() + 4), pygame.SRCALPHA)
    bg_surf_def.fill(bg_color)
    bg_surf_def.blit(def_surf, (4, 2))
    def_rect = bg_surf_def.get_rect(topleft=(10, y_offset))
    surface.blit(bg_surf_def, def_rect)
    y_offset += def_rect.height + 2

    # Agility Text (AGI: xx%)
    agi_perc = player.agility * 100
    agi_text = f"AGI: {agi_perc:.0f}%"
    agi_surf = ui_font.render(agi_text, True, (200, 255, 200)) # Lighter green
    bg_surf_agi = pygame.Surface((agi_surf.get_width() + 8, agi_surf.get_height() + 4), pygame.SRCALPHA)
    bg_surf_agi.fill(bg_color)
    bg_surf_agi.blit(agi_surf, (4, 2))
    agi_rect = bg_surf_agi.get_rect(topleft=(10, y_offset))
    surface.blit(bg_surf_agi, agi_rect)
    y_offset += agi_rect.height + 2

# Note: Dialogue drawing is handled by npc_manager.draw_dialogue() in the main loop