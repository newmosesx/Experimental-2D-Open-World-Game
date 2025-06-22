import pygame
# Import base class and constants
from enemies.enemy_base import Enemy
import enemies.stat_constants as const

# --- Sword Orc Specific Class ---
class Sword_Orc(Enemy):
    def __init__(self, x, y, idle_frames, walk_frames, attack_frames, hurt_frames, death_frames, frame_dims):
        # Define specific properties for Sword_Orc here
        sword_orc_attack_hit_frame = 3 # Example: Hit frame index specific to Sword Orc attack animation

        super().__init__(
            x=x, y=y,
            # Use constants defined for Sword Orc
            health=const.SWORD_ORC_BASE_HEALTH,
            speed=const.SWORD_ORC_BASE_SPEED,
            attack_power=const.SWORD_ORC_ATTACK_POWER,
            attack_range=const.SWORD_ORC_ATTACK_RANGE,
            attack_cooldown=const.SWORD_ORC_ATTACK_COOLDOWN,
            detection_radius=const.SWORD_ORC_DETECTION_RADIUS,
            defense=const.SWORD_ORC_BASE_DEFENSE,
            agility=const.SWORD_ORC_BASE_AGILITY,
            # Pass animation frames and dimensions
            idle_frames=idle_frames,
            walk_frames=walk_frames,
            attack_frames=attack_frames,
            hurt_frames=hurt_frames,
            death_frames=death_frames,
            frame_dims=frame_dims,
            # Specific name and attack timing
            name="Sword_Orc",
            attack_hit_frame_index=sword_orc_attack_hit_frame
        )
        # Sword_Orc specific attributes or overrides can go here
        # Example: maybe different wander radius or chase timeout overrides
        # self.wander_radius = const.SWORD_ORC_WANDER_RADIUS # Already set via constant lookup in base, but could override
        # self.chase_timeout = const.SWORD_ORC_CHASE_TIMEOUT # Same


# --- Add other enemy types here ---
# class Goblin(Enemy):
#     def __init__(self, x, y, idle_frames, walk_frames, attack_frames, hurt_frames, death_frames, frame_dims):
#         goblin_attack_hit_frame = 2 # Different timing maybe
#         super().__init__(...) # Use GOBLIN_ constants

# class Skeleton(Enemy):
#     def __init__(self, x, y, idle_frames, walk_frames, attack_frames, hurt_frames, death_frames, frame_dims):
#          skeleton_attack_hit_frame = 4
#          super().__init__(...) # Use SKELETON_ constants