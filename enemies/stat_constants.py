import pygame
import os # Added for robust font loading

# --- General Combat Constants ---
ANIMATION_SPEED_MS = 150 # Milliseconds between frames
WORLD_WIDTH = 20000
WORLD_HEIGHT = 20000

# --- Dialogue Constants ---
DIALOGUE_COLOR = (255, 255, 255) # White text
DIALOGUE_BG_COLOR = (0, 0, 0, 180) # Semi-transparent black background
DIALOGUE_DEFAULT_DURATION = 3.0 # Seconds dialogue stays visible
DIALOGUE_FONT = None # Initialize
try:
    # Attempt to initialize pygame.font if not already done
    if not pygame.font.get_init():
        pygame.font.init()
    # Try loading a common system font first
    common_fonts = ["Arial", "Verdana", "Calibri", None] # None uses default
    for font_name in common_fonts:
        try:
            DIALOGUE_FONT = pygame.font.SysFont(font_name, 18) # Slightly smaller
            if DIALOGUE_FONT:
                print(f"Dialogue Font: Loaded '{font_name if font_name else 'default sysfont'}' size 18.")
                break
        except Exception:
            continue # Try next font
    if not DIALOGUE_FONT:
         print(f"Warning: Could not load any common system fonts for dialogue.")

except Exception as e:
    print(f"Warning: Error initializing font system or loading dialogue font: {e}")
    DIALOGUE_FONT = None # Ensure it's None if anything failed

# --- Player Constants (Relevant to Combat Interaction) ---
PLAYER_MAX_HEALTH = 100 # Keep player health constant here
PLAYER_HEALTH_REGEN = 0.05 # Health per frame (adjust for balance)
PLAYER_ATTACK_RANGE = 45 # Close to enemy range
PLAYER_ATTACK_POWER = 15
PLAYER_ATTACK_COOLDOWN = 0.8 # Player can attack faster

# --- Sword Orc Specific Constants ---
SWORD_ORC_COUNT = 600 # Keep this here if it's a default spawn count maybe? Or move to spawner logic.
SWORD_ORC_COLOR = (0, 200, 50) # Default color if sprites fail
SWORD_ORC_BASE_HEALTH = 75
SWORD_ORC_BASE_SPEED = 2.5
SWORD_ORC_ATTACK_POWER = 22
SWORD_ORC_ATTACK_RANGE = 35       # Pixel distance for attack trigger
SWORD_ORC_ATTACK_RANGE_BUFFER = 5 # Optional buffer to stop slightly outside exact range
SWORD_ORC_ATTACK_COOLDOWN = 1.5   # Seconds between attacks
SWORD_ORC_DETECTION_RADIUS = 250  # How far SWORD_ORC can 'see' the player
SWORD_ORC_WANDER_RADIUS = 100     # How far SWORD_ORC wanders from spawn point
SWORD_ORC_WANDER_TIME_MIN = 2.0   # Min seconds before changing wander direction
SWORD_ORC_WANDER_TIME_MAX = 5.0   # Max seconds
SWORD_ORC_CHASE_TIMEOUT = 8.0     # Seconds to chase before giving up if player is out of sight
SWORD_ORC_BASE_DEFENSE = 0.10     # 10% damage reduction
SWORD_ORC_BASE_AGILITY = 0.05     # 5% dodge chance

# --- General Enemy Caps / Settings ---
ENEMY_MAX_DEFENSE = 0.90 # Cap
ENEMY_MAX_AGILITY = 0.90 # Cap # Adjusted to match the later definition in original
ENEMY_INVULNERABILITY_DURATION = 0.3 # Seconds of invulnerability after getting hit

# Placeholder Dungeon Tile Constants (used in CombatManager spawn) - Should come from dungeon/world module
TILE_FLOOR = 1
# --- Add constants for other enemy types below as needed ---
# Example:
# GOBLIN_BASE_HEALTH = 30
# GOBLIN_BASE_SPEED = 3.0
# ... etc ...