"""
Combat Mechanics Module Entry Point

This file imports the core components of the combat system (constants, base enemy,
specific enemy types, and the combat manager) to make them easily accessible
for other parts of the application, such as the world structure or game state handler.

Example Usage (in another file like world_struct_stable.py):

import combat_mech_stable as combat

# Assuming animations are loaded elsewhere into 'all_enemy_animations' dictionary
# Assuming world_data, quadtree, point_in_poly_func are available

combat_handler = combat.CombatManager(world_data, quadtree, point_in_poly_func, all_enemy_animations)

# Spawning enemies
combat_handler.spawn_enemies_in_overworld(10)

# In the main game loop update:
combat_handler.update(player_object, dt, current_game_state)

# If player attack hits (determined by player state machine):
combat_handler.handle_player_attack(player_object)

# In the main game loop draw:
combat_handler.draw(screen_surface, camera.apply_point)

"""

# Import constants for potential direct use or inspection elsewhere
import enemies.stat_constants as const
# --- Player Constants (Relevant to Combat Interaction) ---
PLAYER_MAX_HEALTH = 100 # Keep player health constant here
PLAYER_HEALTH_REGEN = 0.05 # Health per frame (adjust for balance)
PLAYER_ATTACK_RANGE = 45 # Close to enemy range
PLAYER_ATTACK_POWER = 15
PLAYER_ATTACK_COOLDOWN = 0.8 # Player can attack faster

# --- Sword Orc Specific Constants ---
SWORD_ORC_COUNT = 600 # Keep this here if it's a default spawn count maybe? Or move to spawner logic.
SWORD_ORC_COLOR = (0, 200, 50) # Default color if sprites fail
SWORD_ORC_BASE_HEALTH = 50
SWORD_ORC_BASE_SPEED = 2.5
SWORD_ORC_ATTACK_POWER = 10
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

# Import the base class (useful for type checking or potential extension)
from enemies.enemy_base import Enemy

# Import specific enemy types (needed by CombatManager and potentially for direct spawning)
from enemies.sword_orc import Sword_Orc
# from .enemy_types import Goblin, Skeleton # Import others if defined

# Import the main manager class
from enemies.combat_manager import CombatManager