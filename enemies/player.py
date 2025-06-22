import pygame
from open_world_dir.ui import ui_font
import combat_mech as combat_mech_stable
import world_struct as world_struct_stable
import asset.assets as assets

# --- Player Class ---
class Player:
    def __init__(self, player_id, x, y, radius, speed, color, animations):
        self.x = x
        self.y = y
        self.player_name = f"{"Play_Tester"}_{player_id}" # Simple name differentiation
        self.level = 0
        self.expirience = 0
        self.player_id = player_id
        self.radius = radius
        self.speed = speed
        self.color = color # Fallback color if sprite fails
        self.rect = pygame.Rect(x - radius, y - radius, radius * 2, radius * 2)
        self.last_direction = pygame.math.Vector2(1, 0) # Default facing right
        self.health = combat_mech_stable.PLAYER_MAX_HEALTH
        self.max_health = combat_mech_stable.PLAYER_MAX_HEALTH
        self.defense = world_struct_stable.PLAYER_BASE_DEFENSE
        self.agility = world_struct_stable.PLAYER_BASE_AGILITY
        self.in_fight = False
        self.is_attacking = False
        self.facing_right = True

        # --- Animation State ---
        self.idle_animation_frames = animations.get('idle')
        self.walk_animation_frames = animations.get('walk')
        self.attack_animation_frames = animations.get('attack')
        self.hurt_animation_frames = animations.get('hurt')
        self.death_animation_frames = animations.get('death')
        frame_dims = animations.get('dims')
        self.frame_width, self.frame_height = frame_dims if frame_dims else (radius * 4, radius * 4)
        self.current_frame_index = 0
        self.last_animation_update = pygame.time.get_ticks()
        self.current_animation_type = 'idle'
        self.animation_finished = True
        self.is_dead = False
        self.is_invulnerable = False
        self.invulnerability_timer = 0.0
        self.invulnerability_duration = 0.5 # seconds

        # <<< NETWORK: State relevant for sending/receiving >>>
        self.last_known_move_vector = pygame.math.Vector2(0, 0)
        self.attack_requested = False # Flag input requests
        self.interact_requested = False

    def handle_input(self):
        keys = pygame.key.get_pressed()
        move_vector = pygame.math.Vector2(0, 0)
        moved = False
        moved_horizontally = False # Track if horizontal keys were pressed

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            move_vector.x = -1; moved = True; moved_horizontally = True
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            move_vector.x = 1; moved = True; moved_horizontally = True
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            move_vector.y = -1; moved = True
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            move_vector.y = 1; moved = True

        # Normalize vector if diagonal movement
        if moved and move_vector.length_squared() > 0:
            move_vector = move_vector.normalize()

        # Store the calculated move vector
        self.last_known_move_vector = move_vector

        # Update facing direction based ONLY on horizontal input press
        if moved_horizontally and move_vector.x != 0:
            self.facing_right = (move_vector.x > 0)
        # Store the last non-zero direction for attacking
        elif move_vector.length_squared() > 0: # If only vertical pressed, update last_direction
            self.last_direction = move_vector.copy()

        # Note: attack_requested and interact_requested are set by KEYDOWN events in main loop now
        return move_vector

    def update(self, move_vector, potential_colliders, dt, world_width, world_height):
        """Updates player state based on movement, animation, and game rules.
           On the server, this is the authoritative update.
           On the client, this is less critical as state is overwritten by server."""
        current_time_ms = pygame.time.get_ticks()

        # --- Invulnerability Timer ---
        if self.is_invulnerable:
            self.invulnerability_timer -= dt
            if self.invulnerability_timer <= 0:
                self.is_invulnerable = False

        # --- Determine Target Base Animation ---
        is_supposed_to_be_moving = move_vector.length_squared() > 0
        target_base_anim = 'walk' if is_supposed_to_be_moving else 'idle'

        # --- Animation State Transitions ---
        previous_animation_type = self.current_animation_type
        is_current_interruptible = self.current_animation_type in ['idle', 'walk']

        if not self.is_dead:
            can_change_state = self.animation_finished or is_current_interruptible
            if can_change_state:
                # If a one-shot animation just finished, revert to idle/walk
                if previous_animation_type in ['hurt', 'attack'] and self.animation_finished:
                    self.current_animation_type = target_base_anim
                # If currently idle/walking, can transition immediately
                elif is_current_interruptible:
                    self.current_animation_type = target_base_anim
            # Reset attack flag specifically when attack animation finishes
            if previous_animation_type == 'attack' and self.animation_finished:
                self.is_attacking = False # Ensure this resets reliably

        # Reset frame index if animation type changed
        if self.current_animation_type != previous_animation_type:
            self.current_frame_index = 0
            # Only non-looping animations truly 'finish' in this state machine sense
            self.animation_finished = (self.current_animation_type in ['idle', 'walk'])
            # Ensure is_attacking is true ONLY when attack animation starts
            self.is_attacking = (self.current_animation_type == 'attack')

        # --- Select Current Animation Frames ---
        current_frames = None
        is_one_shot_animation = False
        if self.current_animation_type == 'idle': current_frames = self.idle_animation_frames
        elif self.current_animation_type == 'walk': current_frames = self.walk_animation_frames
        elif self.current_animation_type == 'attack': current_frames = self.attack_animation_frames; is_one_shot_animation = True
        elif self.current_animation_type == 'hurt': current_frames = self.hurt_animation_frames; is_one_shot_animation = True
        elif self.current_animation_type == 'death': current_frames = self.death_animation_frames; is_one_shot_animation = True

        # --- Animation Progression ---
        if current_frames and not self.animation_finished:
            anim_speed = assets.ANIMATION_SPEED_MS # Use constant from assets
            if current_time_ms - self.last_animation_update > anim_speed:
                next_frame_index = self.current_frame_index + 1
                if next_frame_index >= len(current_frames):
                    if is_one_shot_animation:
                        self.animation_finished = True
                        # Hold last frame for death, otherwise allow transition
                        if self.current_animation_type == 'death':
                             self.current_frame_index = len(current_frames) - 1
                        # else: # Let state transition handle reset for hurt/attack
                        #     self.current_frame_index = 0 # Or let state machine handle transition
                    else: # Loop idle/walk
                        self.current_frame_index = 0
                else:
                    self.current_frame_index = next_frame_index
                self.last_animation_update = current_time_ms

        # --- Movement Lock and Speed Calculation ---
        # Player can only move if not dead and in an interruptible state (idle/walk)
        can_move = (self.current_animation_type in ['idle', 'walk']) and not self.is_dead
        effective_speed = self.speed if can_move else 0
        final_move_vector = move_vector * effective_speed

        # --- Movement & Collision ---
        if final_move_vector.length_squared() > 0:
            prev_x, prev_y = self.x, self.y
            # Adjust speed based on delta time (scale by FPS target for consistency)
            move_delta_x = final_move_vector.x * dt * 60
            move_delta_y = final_move_vector.y * dt * 60

            # Move X
            self.x += move_delta_x
            self.rect.centerx = int(round(self.x)) # Use round for better centering
            for obstacle in potential_colliders:
                if self.rect.colliderect(obstacle):
                    if move_delta_x > 0: # Moving right
                        self.rect.right = obstacle.left
                    elif move_delta_x < 0: # Moving left
                        self.rect.left = obstacle.right
                    self.x = float(self.rect.centerx) # Update float pos from collision corrected rect
                    break # Stop checking collisions for this axis

            # Move Y
            self.y += move_delta_y
            self.rect.centery = int(round(self.y))
            for obstacle in potential_colliders:
                if self.rect.colliderect(obstacle):
                    if move_delta_y > 0: # Moving down
                        self.rect.bottom = obstacle.top
                    elif move_delta_y < 0: # Moving up
                        self.rect.top = obstacle.bottom
                    self.y = float(self.rect.centery) # Update float pos from collision corrected rect
                    break # Stop checking collisions for this axis

            # Final position update from rect (redundant if updated above, but safe)
            self.x = float(self.rect.centerx)
            self.y = float(self.rect.centery)

        # --- World Boundary Check ---
        self.x = max(self.radius, min(self.x, world_width - self.radius))
        self.y = max(self.radius, min(self.y, world_height - self.radius))
        self.rect.center = (int(round(self.x)), int(round(self.y))) # Update rect final position

        # --- Passive Health Regeneration ---
        if self.in_fight and self.health < self.max_health and not self.is_dead:
            regen_amount = combat_mech_stable.PLAYER_HEALTH_REGEN * dt * 60 # Scale by FPS target
            self.health = min(self.health + regen_amount, self.max_health)

    def draw(self, surface, camera_apply_point_func, is_local_player):
        player_screen_pos = camera_apply_point_func(self.x, self.y)
        current_frame_image = None
        current_frames = None

        # Select frame list based on current animation type
        if self.current_animation_type == 'idle': current_frames = self.idle_animation_frames
        elif self.current_animation_type == 'walk': current_frames = self.walk_animation_frames
        elif self.current_animation_type == 'attack': current_frames = self.attack_animation_frames
        elif self.current_animation_type == 'hurt': current_frames = self.hurt_animation_frames
        elif self.current_animation_type == 'death': current_frames = self.death_animation_frames

        # Get the specific frame, ensuring index is valid
        if current_frames:
            # Ensure index is within bounds, especially if animation finished mid-frame
            safe_frame_index = min(self.current_frame_index, len(current_frames) - 1)
            if safe_frame_index >= 0:
                 current_frame_image = current_frames[safe_frame_index]

        # Draw the frame if available
        if current_frame_image:
            image_to_draw = current_frame_image
            # Flip image based on facing direction
            if not self.facing_right:
                image_to_draw = pygame.transform.flip(current_frame_image, True, False)

            # Calculate top-left position for blitting (center sprite on player pos)
            draw_x = player_screen_pos[0] - self.frame_width // 2
            draw_y = player_screen_pos[1] - self.frame_height // 2

            # --- Invulnerability Flash ---
            if self.is_invulnerable:
                # Simple flash: alternate drawing based on timer
                if int(self.invulnerability_timer * 10) % 2 == 0: # Flash roughly 5 times/sec
                    surface.blit(image_to_draw, (draw_x, draw_y))
            else:
                surface.blit(image_to_draw, (draw_x, draw_y))
            
             # Draw Player Name/ID above head
            if ui_font:
                name_text = self.player_name if is_local_player else f"P{self.player_id}"
                name_color = (255, 255, 255) if is_local_player else (200, 200, 255)
                name_surf = ui_font.render(name_text, True, name_color)
                name_rect = name_surf.get_rect(centerx=player_screen_pos[0], bottom=draw_y - 2)
                surface.blit(name_surf, name_rect)
                

        else: # Fallback: Draw a circle if sprite is missing
            pygame.draw.circle(surface, self.color, player_screen_pos, self.radius)
            if ui_font: # Draw name even for fallback
                name_text = self.player_name if is_local_player else f"P{self.player_id}"
                name_color = (255, 255, 255) if is_local_player else (200, 200, 255)
                name_surf = ui_font.render(name_text, True, name_color)
                name_rect = name_surf.get_rect(centerx=player_screen_pos[0], bottom=player_screen_pos[1] - self.radius - 2)
                surface.blit(name_surf, name_rect)

    def take_damage(self, amount):
        if self.is_dead or self.is_invulnerable: return 0 # Cannot take damage if already dead or invulnerable

        # --- Apply Defense ---
        effective_defense = max(0.0, min(self.defense, world_struct_stable.PLAYER_MAX_DEFENSE))
        damage_multiplier = max(0.0, 1.0 - effective_defense) # Ensure multiplier doesn't go below 0
        actual_damage = round(amount * damage_multiplier) # Round damage to nearest integer

        # Prevent taking less than 1 damage if the base damage was positive
        if amount > 0 and actual_damage < 1:
            actual_damage = 1

        self.health -= actual_damage
        print(f"Player took {actual_damage} damage ({amount} base, {effective_defense*100:.0f}% DEF)! HP: {self.health}/{self.max_health}")
        self.in_fight = True # Reset regen timer

        if self.health <= 0:
            self.health = 0
            if not self.is_dead: # Trigger death sequence only once
                print("Player Defeated!")
                self.is_dead = True
                self.current_animation_type = 'death'
                self.current_frame_index = 0
                self.animation_finished = False # Start the death animation
        else:
            # Took damage but not dead, trigger hurt animation
            self.current_animation_type = 'hurt'
            self.current_frame_index = 0
            self.animation_finished = False # Start the hurt animation
            self.is_invulnerable = True # Grant invulnerability
            self.invulnerability_timer = self.invulnerability_duration
        
        return actual_damage

    def start_attack_animation(self):
        # Only start attack if idle or walking (and previous animation is finished)
        # Also check not already attacking or dead
        if (self.current_animation_type in ['idle', 'walk'] and self.animation_finished and
                not self.is_attacking and not self.is_dead):
            self.current_animation_type = 'attack'
            self.current_frame_index = 0
            self.animation_finished = False
            self.is_attacking = True # Set attack flag immediately
            print(f"Player {self.player_id} attack started") # Debug
            return True # Attack animation successfully started
        # print(f"Could not start attack: state={self.current_animation_type}, finished={self.animation_finished}, attacking={self.is_attacking}, dead={self.is_dead}") # Debug if needed
        return False # Could not start attack

    # <<< NETWORK: Method to get serializable state >>>
    def get_network_state(self):
        """Returns a dictionary of the player's state for network transmission."""
        return {
            'id': self.player_id,
            'x': self.x,
            'y': self.y,
            'health': self.health,
            'max_health': self.max_health, # Good to send for UI
            'facing_right': self.facing_right,
            'anim_type': self.current_animation_type,
            'anim_frame': self.current_frame_index,
            'anim_finished': self.animation_finished, # Important for one-shot anims
            'is_dead': self.is_dead,
            'is_invulnerable': self.is_invulnerable, # For client-side effects
            # Add other relevant states like defense, agility if they can change dynamically
            'defense': self.defense,
            'agility': self.agility,
            'is_attacking': self.is_attacking, # Sync attack state
        }

    # <<< NETWORK: Method to update state from network data >>>
    def apply_network_state(self, state_data):
        """Updates the player's attributes based on received network data."""
        # Directly update core attributes
        self.x = state_data.get('x', self.x)
        self.y = state_data.get('y', self.y)
        self.health = state_data.get('health', self.health)
        self.max_health = state_data.get('max_health', self.max_health)
        self.facing_right = state_data.get('facing_right', self.facing_right)
        self.is_dead = state_data.get('is_dead', self.is_dead)
        self.is_invulnerable = state_data.get('is_invulnerable', self.is_invulnerable)
        self.defense = state_data.get('defense', self.defense)
        self.agility = state_data.get('agility', self.agility)
        self.is_attacking = state_data.get('is_attacking', self.is_attacking)

        # Update animation state carefully
        new_anim_type = state_data.get('anim_type', self.current_animation_type)
        new_anim_frame = state_data.get('anim_frame', self.current_frame_index)
        new_anim_finished = state_data.get('anim_finished', self.animation_finished)

        # Only reset frame index if the animation *type* changes
        if new_anim_type != self.current_animation_type:
            self.current_animation_type = new_anim_type
            self.current_frame_index = new_anim_frame # Use server's frame index on change
        elif self.current_animation_type == new_anim_type:
             # If type is same, only update frame if server frame is different (avoids jitter)
             # Maybe add a small tolerance or only update if server frame is ahead?
             # Simple approach: always sync frame if type is same.
             self.current_frame_index = new_anim_frame

        self.animation_finished = new_anim_finished

        # Update the rect based on new position
        self.rect.center = (int(self.x), int(self.y))