import pygame
import random
import math
# Import constants using a clear alias or specific names
from .stat_constants import *

class Enemy:
    # <<< NETWORK: Added unique ID >>>
    _enemy_id_counter = 0
    def __init__(self, x, y, health, speed, attack_power, attack_range, attack_cooldown, detection_radius,
                 defense, agility, idle_frames, walk_frames, attack_frames, hurt_frames, death_frames,
                 frame_dims, name="Enemy", attack_hit_frame_index=None):

        self.id = Enemy._enemy_id_counter
        Enemy._enemy_id_counter += 1
        self.enemy_type = name # Store the type name (e.g., "Sword_Orc")

        self.x = float(x); self.y = float(y); self.spawn_x = float(x); self.spawn_y = float(y)
        self.health = health; self.max_health = health
        self.speed = speed; self.attack_power = attack_power; self.attack_range = attack_range
        # Use constants for range buffer
        self.stopping_range = max(5, attack_range - SWORD_ORC_ATTACK_RANGE_BUFFER) # Example: use SWORD_ORC buffer, or make generic ENEMY_ATTACK_RANGE_BUFFER
        self.stopping_range_sq = self.stopping_range * self.stopping_range
        self.attack_trigger_range_sq = attack_range * attack_range
        self.attack_cooldown_timer = 0.0; self.attack_cooldown_duration = attack_cooldown
        self.detection_radius_sq = detection_radius * detection_radius

        # Use generic enemy caps
        self.defense = max(0.0, min(defense, ENEMY_MAX_DEFENSE))
        self.agility = max(0.0, min(agility, ENEMY_MAX_AGILITY))

        self.state = 'idle' # idle, walking, chasing, returning, attacking, hurt, dead
        self.target_player = None # <<< NETWORK: Store the player object being targeted >>>
        self.target_position = None
        self.wander_timer = random.uniform(SWORD_ORC_WANDER_TIME_MIN, SWORD_ORC_WANDER_TIME_MAX)
        self.chase_timer = 0.0
        self.wander_radius = SWORD_ORC_WANDER_RADIUS
        self.chase_timeout = SWORD_ORC_CHASE_TIMEOUT

        # Rect and facing
        self.radius = frame_dims[0] / 4 if frame_dims else 10
        self.rect = pygame.Rect(x - self.radius, y - self.radius, self.radius * 2, self.radius * 2)
        self.last_direction = pygame.math.Vector2(1, 0)
        self.facing_right = True
        self.name = name
        self.said_greeting = False # Specific dialogue trigger flag

        # --- Animation State ---
        self.idle_animation_frames = idle_frames
        self.walk_animation_frames = walk_frames
        self.attack_animation_frames = attack_frames
        self.hurt_animation_frames = hurt_frames
        self.death_animation_frames = death_frames
        self.frame_width, self.frame_height = frame_dims if frame_dims else (self.radius*2, self.radius*2)
        self.current_frame_index = 0
        self.last_animation_update = pygame.time.get_ticks()
        self.current_animation_type = 'idle' # idle, walk, attack, hurt, death
        self.animation_finished = True
        self.is_dead = False
        self.is_attacking = False
        self.is_invulnerable = False
        self.invulnerability_timer = 0.0
        self.invulnerability_duration = ENEMY_INVULNERABILITY_DURATION

        # --- Dialogue Attributes ---
        self.dialogue_text = None
        self.dialogue_timer = 0.0

        # --- Attack Timing Attributes ---
        num_attack_frames = len(self.attack_animation_frames) if self.attack_animation_frames else 0
        if attack_hit_frame_index is None and num_attack_frames > 1:
            # Default hit frame (e.g., 60% through animation)
            self.attack_hit_frame_index = max(0, min(int(num_attack_frames * 0.6), num_attack_frames - 1))
        elif attack_hit_frame_index is not None:
            # Use provided index, ensuring it's valid
            self.attack_hit_frame_index = max(0, min(attack_hit_frame_index, num_attack_frames - 1)) if num_attack_frames > 0 else -1
        else: # No frames or index provided
            self.attack_hit_frame_index = -1
        self.attack_hit_triggered_this_cycle = False


    def set_dialogue(self, text, duration=DIALOGUE_DEFAULT_DURATION):
        """Sets the dialogue text and starts the timer."""
        if DIALOGUE_FONT: # Only set if font loaded
            self.dialogue_text = text
            self.dialogue_timer = duration
        else:
            # Fallback to print if font failed
            print(f"{self.name} ({self.id}) says: {text} (Dialogue font failed)")

    # <<< NETWORK: Update now takes dictionary of players >>>
    def update(self, network_players, dt, colliders_nearby, game_state, quadtree, is_point_in_polygon):
        """ Server-side authoritative update logic for the enemy. """
        current_time_ms = pygame.time.get_ticks()
        previous_state_for_dialogue = self.state

        # --- Timers ---
        self.attack_cooldown_timer = max(0.0, self.attack_cooldown_timer - dt)
        self.wander_timer = max(0.0, self.wander_timer - dt)
        if self.is_invulnerable:
            self.invulnerability_timer -= dt
            if self.invulnerability_timer <= 0: self.is_invulnerable = False

        if self.dialogue_timer > 0:
            self.dialogue_timer -= dt
            if self.dialogue_timer <= 0:
                self.dialogue_text = None

        # --- State Logic (Determine the INTENDED action/state) ---
        if self.is_dead:
            self.state = 'dead'

        if self.state != 'dead' and not (self.state == 'hurt' and not self.animation_finished):
            # --- Find Closest Visible Player ---
            closest_player = None
            min_dist_sq = self.detection_radius_sq # Start with max detection range

            # Iterate through the dictionary of player objects
            for p_id, player in network_players.items():
                if player and not player.is_dead: # Check if player object exists and is alive
                    dist_sq = (player.x - self.x)**2 + (player.y - self.y)**2
                    if dist_sq < min_dist_sq:
                        # Basic line of sight check (optional, can be complex)
                        # For now, assume if within radius, can be seen
                        # if is_visible(self.x, self.y, player.x, player.y, colliders_nearby):
                        min_dist_sq = dist_sq
                        closest_player = player

            # --- React Based on Closest Player ---
            self.target_player = closest_player # Update target player reference

            if self.target_player: # If a player is visible and targeted
                self.chase_timer = SWORD_ORC_CHASE_TIMEOUT # Reset chase timer while seeing a player

                # Use attack_trigger_range_sq for ATTACK DECISION
                if min_dist_sq < self.attack_trigger_range_sq and self.attack_cooldown_timer <= 0:
                    if self.state != 'hurt': # Don't attack if recovering from hit
                        self.state = 'attacking'
                        self.target_position = None # Stop pathfinding when attacking
                elif self.state not in ['attacking', 'hurt']: # If not attacking or hurt
                     # Use stopping_range_sq to decide if needing to move closer
                     if min_dist_sq > self.stopping_range_sq:
                          self.state = 'chasing'
                          # Target the player's current position
                          self.target_position = pygame.math.Vector2(self.target_player.x, self.target_player.y)
                     else:
                          # Within stopping range, but maybe not attack range/cooldown ready
                          # Stop moving, wait for attack opportunity (state remains 'chasing' intention but movement stops)
                          self.state = 'chasing' # Still intends to chase/attack
                          self.target_position = None # Clear pathfinding target
                # Let attack animation finish even if player moves slightly out of range
                elif self.state == 'attacking' and min_dist_sq >= self.attack_trigger_range_sq:
                     pass # Animation state machine handles transition after anim finishes

            else: # Player not visible or dead, or no players left
                self.target_player = None # Clear target player
                if self.state == 'chasing' or self.state == 'attacking': # Was chasing or attacking?
                    self.chase_timer -= dt
                    if self.chase_timer <= 0:
                         # Give up chase, return to spawn
                         self.state = 'returning'
                         self.target_position = pygame.math.Vector2(self.spawn_x, self.spawn_y)
                    # else: keep chasing last known spot? Or just switch to return? Let's return.
                elif self.state == 'returning':
                    # Check if close enough to spawn point
                    dist_to_spawn_sq = (self.x - self.spawn_x)**2 + (self.y - self.spawn_y)**2
                    # Use a small threshold to stop jittering at spawn
                    if dist_to_spawn_sq < (self.speed * dt * 10)**2:
                        self.state = 'idle'
                        self.target_position = None
                    else: # Continue moving towards spawn
                        self.target_position = pygame.math.Vector2(self.spawn_x, self.spawn_y)
                elif self.state == 'wander':
                    if self.target_position is None or self.wander_timer <= 0:
                        # Wander finished or timer expired, go idle
                        self.state = 'idle'
                        self.wander_timer = random.uniform(SWORD_ORC_WANDER_TIME_MIN, SWORD_ORC_WANDER_TIME_MAX)
                    else:
                        # Check if reached wander target
                        dist_to_target_sq = (self.x - self.target_position.x)**2 + (self.y - self.target_position.y)**2
                        if dist_to_target_sq < (self.speed * dt * 10)**2: # Close enough
                            self.state = 'idle'
                            self.target_position = None
                            self.wander_timer = random.uniform(SWORD_ORC_WANDER_TIME_MIN, SWORD_ORC_WANDER_TIME_MAX)
                elif self.state == 'idle':
                    # If idle timer expired, start wandering
                    if self.wander_timer <= 0:
                        # Choose a random wander point near spawn
                        angle = random.uniform(0, 2 * math.pi)
                        dist = random.uniform(0, SWORD_ORC_WANDER_RADIUS)
                        max_dist_from_spawn = SWORD_ORC_WANDER_RADIUS * 1.5 # Limit wander distance
                        target_x = self.spawn_x + dist * math.cos(angle)
                        target_y = self.spawn_y + dist * math.sin(angle)
                        # Clamp target to stay somewhat near spawn area
                        target_x = max(self.spawn_x - max_dist_from_spawn, min(target_x, self.spawn_x + max_dist_from_spawn))
                        target_y = max(self.spawn_y - max_dist_from_spawn, min(target_y, self.spawn_y + max_dist_from_spawn))
                        self.target_position = pygame.math.Vector2(target_x, target_y)
                        self.state = 'wander'


        # --- Movement Calculation (Based on target_position) ---
        move_vector = pygame.math.Vector2(0, 0)
        should_move = False # Flag if movement should occur

        # Determine if movement is needed based on state and target
        if self.state in ['wander', 'returning'] and self.target_position:
             direction = self.target_position - pygame.math.Vector2(self.x, self.y)
             dist_to_target_sq = direction.length_squared()
             if dist_to_target_sq > (self.speed * dt * 10)**2: # Jitter prevention threshold
                  should_move = True
        elif self.state == 'chasing' and self.target_player:
             # Check distance to the *current* player position
             player_pos = pygame.math.Vector2(self.target_player.x, self.target_player.y)
             direction = player_pos - pygame.math.Vector2(self.x, self.y)
             dist_to_target_sq = direction.length_squared()
             # Move only if further than stopping range
             if dist_to_target_sq > self.stopping_range_sq:
                  should_move = True
                  self.target_position = player_pos # Update pathfinding target
             else:
                  # Within stopping range, don't move, clear pathfinding target
                  self.target_position = None
                  should_move = False
                  # Update facing direction even when stopped
                  if dist_to_target_sq > 1:
                       norm_direction = direction.normalize()
                       self.last_direction = norm_direction.copy()
                       self.facing_right = (norm_direction.x >= 0)


        # Calculate move_vector if movement should occur
        if should_move and self.target_position:
            direction = self.target_position - pygame.math.Vector2(self.x, self.y)
            if direction.length_squared() > 1: # Avoid normalizing zero vector
                move_vector = direction.normalize()
                self.last_direction = move_vector.copy()
                self.facing_right = (move_vector.x >= 0)
            else:
                move_vector = pygame.math.Vector2(0, 0)
        else: # Not moving or no target
            move_vector = pygame.math.Vector2(0, 0)

        # Determine Target Base Animation (idle or walk)
        target_base_anim = 'walk' if move_vector.length_squared() > 0 else 'idle'

        # --- Animation State Machine ---
        previous_animation_type = self.current_animation_type
        new_animation_type = previous_animation_type

        # 1. DEAD State
        if self.state == 'dead':
            if self.current_animation_type != 'death':
                new_animation_type = 'death'; self.animation_finished = False; self.is_attacking = False
        # 2. HURT State
        elif self.state == 'hurt':
             # If not already hurt or dead, switch to hurt anim
            if self.current_animation_type not in ['hurt', 'death']:
                 # Interrupt other actions
                new_animation_type = 'hurt'; self.animation_finished = False; self.is_attacking = False
            elif self.current_animation_type == 'hurt' and self.animation_finished:
                # Hurt finished, revert to base state (re-evaluate targeting)
                # Note: State logic above already finds the closest player
                if self.target_player:
                    dist_sq = (self.target_player.x - self.x)**2 + (self.target_player.y - self.y)**2
                    if dist_sq < self.attack_trigger_range_sq and self.attack_cooldown_timer <= 0:
                        self.state = 'attacking'
                        new_animation_type = 'attack' # Try to attack immediately
                        self.animation_finished = False
                        self.is_attacking = True
                        self.attack_hit_triggered_this_cycle = False
                    else:
                         # Check if need to move closer or just idle/wait
                         if dist_sq > self.stopping_range_sq:
                              self.state = 'chasing'
                              new_animation_type = 'walk'
                         else:
                              self.state = 'chasing' # Intent is chase, but stopped
                              new_animation_type = 'idle'
                else: # No target after being hurt
                    self.state = 'idle' # Revert to idle
                    new_animation_type = 'idle'

        # 3. ATTACK State
        elif self.state == 'attacking':
            can_start_attack_anim = (
                self.current_animation_type != 'attack' and
                self.current_animation_type not in ['hurt', 'death'] and
                (self.animation_finished or self.current_animation_type in ['idle', 'walk'])
            )
            if can_start_attack_anim:
                # Start the attack animation
                new_animation_type = 'attack'; self.animation_finished = False
                self.is_attacking = True; self.attack_hit_triggered_this_cycle = False
            elif self.current_animation_type == 'attack' and self.animation_finished:
                # Attack animation finished
                self.is_attacking = False
                # Reset attack cooldown timer
                self.attack_cooldown_timer = self.attack_cooldown_duration
                # Re-evaluate state after attack
                if self.target_player: # Check if target still exists
                    dist_sq = (self.target_player.x - self.x)**2 + (self.target_player.y - self.y)**2
                    if dist_sq < self.attack_trigger_range_sq and self.attack_cooldown_timer <= 0: # Can we attack again immediately? (Unlikely due to cooldown)
                         new_animation_type = 'attack'; self.animation_finished = False
                         self.is_attacking = True; self.attack_hit_triggered_this_cycle = False
                    else:
                         # Need to chase or just wait?
                         if dist_sq > self.stopping_range_sq:
                              self.state = 'chasing'
                              new_animation_type = 'walk'
                         else:
                              self.state = 'chasing' # Intend to chase, but stopped
                              new_animation_type = 'idle'
                else: # Target lost after attack
                    self.state = 'idle' # Revert to idle or maybe return?
                    new_animation_type = 'idle'


        # 4. Base Movement State (Idle, Walk, Wander, Return, Chase(stopped))
        elif self.state not in ['dead', 'hurt', 'attacking']:
             # Allow switching between idle/walk if previous anim finished or interruptible
            if self.animation_finished or self.current_animation_type in ['idle', 'walk']:
                if self.current_animation_type != target_base_anim:
                     new_animation_type = target_base_anim

        # Apply Animation Change
        if new_animation_type != previous_animation_type:
            self.current_animation_type = new_animation_type
            self.current_frame_index = 0
            self.animation_finished = (new_animation_type in ['idle', 'walk']) # Looping anims don't 'finish' in one cycle
            # Reset attack flags if changing away from attack
            if previous_animation_type == 'attack' and new_animation_type != 'attack':
                 if self.is_attacking: self.is_attacking = False
                 self.attack_hit_triggered_this_cycle = False # Reset hit flag

        # Final State Consistency Check
        if self.current_animation_type != 'attack' and self.is_attacking: self.is_attacking = False
        # Ensure is_attacking is True if attack anim is playing and not finished
        if self.current_animation_type == 'attack' and not self.is_attacking and not self.animation_finished:
             self.is_attacking = True


        # --- Select Current Animation Frames --- (No changes needed)
        current_frames = None; is_one_shot_animation = False; looping_animation = False
        if self.current_animation_type == 'idle': current_frames = self.idle_animation_frames; looping_animation = True
        elif self.current_animation_type == 'walk': current_frames = self.walk_animation_frames; looping_animation = True
        elif self.current_animation_type == 'attack': current_frames = self.attack_animation_frames; is_one_shot_animation = True
        elif self.current_animation_type == 'hurt': current_frames = self.hurt_animation_frames; is_one_shot_animation = True
        elif self.current_animation_type == 'death': current_frames = self.death_animation_frames; is_one_shot_animation = True

        # --- Animation Progression & Hit Frame Check ---
        triggered_hit_this_frame = False # Flag to return
        if current_frames and len(current_frames) > 0:
            anim_speed = ANIMATION_SPEED_MS # Use constant speed
            # Check if frame should advance
            advance_frame = (not self.animation_finished) or \
                            (self.current_animation_type == 'death' and self.current_frame_index < len(current_frames) - 1) # Allow death anim to reach last frame

            if advance_frame and (current_time_ms - self.last_animation_update > anim_speed):
                previous_frame_index = self.current_frame_index # Store previous frame for hit check
                next_frame_index = self.current_frame_index + 1

                if next_frame_index >= len(current_frames): # Reached end of animation
                    if is_one_shot_animation:
                        self.animation_finished = True
                        # Hold last frame for death, otherwise reset index (state machine handles transition)
                        self.current_frame_index = len(current_frames) - 1 if self.current_animation_type == 'death' else 0
                        # Reset attack-specific flags if attack animation finished
                        if self.current_animation_type == 'attack':
                            # Cooldown reset is now handled in the state logic after anim finishes
                            self.attack_hit_triggered_this_cycle = False # Reset flag for next attack
                    elif looping_animation: # Loop idle/walk
                         self.current_frame_index = 0
                         self.animation_finished = False # Looping never truly 'finishes'
                    else: # Should not happen if flags are set correctly
                         self.current_frame_index = 0
                         self.animation_finished = True
                else: # Advance to next frame
                    self.current_frame_index = next_frame_index
                    self.animation_finished = False # Still playing

                # Check if the attack hit frame was crossed
                if self.current_animation_type == 'attack' and \
                   self.is_attacking and \
                   not self.attack_hit_triggered_this_cycle and \
                   self.attack_hit_frame_index >= 0 and \
                   self.current_frame_index >= self.attack_hit_frame_index and \
                   previous_frame_index < self.attack_hit_frame_index: # Check if just passed the hit frame
                        self.attack_hit_triggered_this_cycle = True # Mark hit as triggered for this attack cycle
                        triggered_hit_this_frame = True # Signal main loop to check for damage

                self.last_animation_update = current_time_ms # Update time even if frame index didn't change (e.g. held last death frame)

        elif not current_frames or len(current_frames) == 0: # No frames for current anim type
             self.animation_finished = True # Consider animation finished


        # --- Movement Application & Collision (AUTHORITATIVE on Server) ---
        # Check if movement is allowed based on animation state and if a move vector exists
        can_move_now = (self.current_animation_type in ['idle', 'walk'] or (self.current_animation_type == 'attack' and self.animation_finished)) and \
                       not self.is_dead and \
                       move_vector.length_squared() > 0 # Check if move_vector is non-zero

        effective_speed = self.speed if can_move_now else 0
        final_move_vector = move_vector * effective_speed * dt * 60 # Apply speed and scale by FPS

        if final_move_vector.length_squared() > 0: # Only apply movement if vector is non-zero
            # Store position before moving
            prev_x, prev_y = self.x, self.y

            # Move X
            self.x += final_move_vector.x
            self.rect.centerx = int(self.x)
            collided_x = False
            for obstacle in colliders_nearby:
                if self.rect.colliderect(obstacle):
                    if final_move_vector.x > 0: self.rect.right = obstacle.left
                    elif final_move_vector.x < 0: self.rect.left = obstacle.right
                    self.x = self.rect.centerx
                    collided_x = True
                    break

            # Move Y
            self.y += final_move_vector.y
            self.rect.centery = int(self.y)
            collided_y = False
            for obstacle in colliders_nearby:
                if self.rect.colliderect(obstacle):
                    if final_move_vector.y > 0: self.rect.bottom = obstacle.top
                    elif final_move_vector.y < 0: self.rect.top = obstacle.bottom
                    self.y = self.rect.centery
                    collided_y = True
                    break

            # Update final position from potentially adjusted rect
            self.x = self.rect.centerx
            self.y = self.rect.centery

            # World boundary clamp (Get bounds from world_struct or config)
            world_w = 20000 # Placeholder - use actual effective world size
            world_h = 20000
            self.x = max(self.radius, min(self.x, world_w - self.radius))
            self.y = max(self.radius, min(self.y, world_h - self.radius))
            self.rect.center = (int(self.x), int(self.y))


        # --- Dialogue Trigger ---
        if self.target_player and self.state in ['chasing', 'attacking'] and previous_state_for_dialogue not in ['chasing', 'attacking'] and not self.said_greeting:
            if self.name == "Sword_Orc":
                self.set_dialogue("Meat?") # Example greeting
            self.said_greeting = True
        elif not self.target_player and self.state not in ['chasing', 'attacking']:
            self.said_greeting = False # Reset greeting flag when not targeting

        # Return whether an attack hit was triggered in this frame update
        return triggered_hit_this_frame


    def draw(self, surface, camera_apply_point_func):
        """ Draws the enemy sprite based on current animation state. """
        enemy_screen_pos = camera_apply_point_func(self.x, self.y)
        current_frame_image = None
        current_frames = None

        # Select frame set based on current animation type
        if self.current_animation_type == 'idle': current_frames = self.idle_animation_frames
        elif self.current_animation_type == 'walk': current_frames = self.walk_animation_frames
        elif self.current_animation_type == 'attack': current_frames = self.attack_animation_frames
        elif self.current_animation_type == 'hurt': current_frames = self.hurt_animation_frames
        elif self.current_animation_type == 'death': current_frames = self.death_animation_frames

        # Get the specific frame image, ensuring index is valid
        if current_frames and len(current_frames) > 0:
            safe_frame_index = max(0, min(self.current_frame_index, len(current_frames) - 1))
            try:
                current_frame_image = current_frames[safe_frame_index]
            except IndexError:
                 print(f"WARN: Frame index {safe_frame_index} out of bounds for anim '{self.current_animation_type}' (len {len(current_frames)}) for Enemy {self.id}")
                 current_frame_image = None

        # Draw the image or fallback shape
        if current_frame_image:
            image_to_draw = current_frame_image
            # Flip image based on facing direction
            if not self.facing_right:
                image_to_draw = pygame.transform.flip(current_frame_image, True, False)
            # Calculate draw position (top-left corner)
            draw_x = enemy_screen_pos[0] - self.frame_width // 2
            draw_y = enemy_screen_pos[1] - self.frame_height // 2

            # Apply invulnerability blink effect
            if self.is_invulnerable:
                 # Simple blink effect
                 if int(pygame.time.get_ticks() / 100) % 2 == 0:
                      surface.blit(image_to_draw, (draw_x, draw_y))
            else:
                 surface.blit(image_to_draw, (draw_x, draw_y))

            # Draw Health Bar (Optional)
            # ... (health bar drawing logic) ...

        else: # Fallback circle if no image/frames
             # Use enemy color or default
             color = getattr(self, 'color', (200, 0, 0)) # Use self.color if defined, else default
             # Apply invulnerability blink effect
             if self.is_invulnerable and pygame.time.get_ticks() % 200 < 100:
                  pass # Don't draw
             else:
                  pygame.draw.circle(surface, color, enemy_screen_pos, int(self.radius))

        # <<< Draw Dialogue >>>
        if self.dialogue_text and self.dialogue_timer > 0 and DIALOGUE_FONT:
            try:
                # Render text
                text_surface = DIALOGUE_FONT.render(self.dialogue_text, True, DIALOGUE_COLOR)
                text_rect = text_surface.get_rect()

                # Position above the enemy sprite
                text_rect.centerx = enemy_screen_pos[0]
                # Adjust vertical position based on frame height
                text_rect.bottom = enemy_screen_pos[1] - (self.frame_height // 2) - 5

                # Draw background
                bg_rect = text_rect.inflate(6, 4) # Add padding
                temp_surface = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
                pygame.draw.rect(temp_surface, DIALOGUE_BG_COLOR, temp_surface.get_rect(), border_radius=3)
                surface.blit(temp_surface, bg_rect.topleft)

                # Draw the actual text
                surface.blit(text_surface, text_rect.topleft)
            except Exception as e: # Catch potential font rendering errors
                print(f"Error rendering dialogue for {self.name} ({self.id}): {e}")
                self.dialogue_text = None # Stop trying to render


    def take_damage(self, amount):
        """Applies damage, defense, triggers hurt/death state. (Server Authority)"""
        if self.is_dead or self.is_invulnerable: return 0 # Return 0 damage taken

        # Apply Defense
        damage_multiplier = max(0.0, 1.0 - self.defense)
        actual_damage = round(amount * damage_multiplier)
        if actual_damage <= 0 and amount > 0 and self.defense < 1.0: actual_damage = 1 # Min 1 damage

        self.health -= actual_damage
        # print(f"{self.name} ({self.id}) took {actual_damage} damage ({amount} base). Health: {self.health}/{self.max_health}") # Debug

        if self.health <= 0:
            self.health = 0
            if not self.is_dead:
                # print(f"{self.name} ({self.id}) defeated!") # Debug
                self.is_dead = True
                self.state = 'dead' # Set final state
                if self.current_animation_type != 'death':
                    self.current_animation_type = 'death'
                    self.current_frame_index = 0
                    self.animation_finished = False # Start the animation
                self.is_attacking = False # Cannot attack while dead
                self.target_player = None # Clear target
                self.target_position = None
        else:
            # Took damage but not dead, trigger hurt state and animation
            self.state = 'hurt'
            if self.current_animation_type != 'hurt':
                 self.current_animation_type = 'hurt'
                 self.current_frame_index = 0
                 self.animation_finished = False # Start the animation
            self.is_attacking = False # Hurt interrupts attack
            self.is_invulnerable = True
            self.invulnerability_timer = self.invulnerability_duration

        return actual_damage # Return actual damage dealt

    # <<< NETWORK: Method to get serializable state >>>
    def get_network_state(self):
        """Returns a dictionary of the enemy's state for network transmission."""
        return {
            'id': self.id,
            'type': self.enemy_type, # Important for client to know what kind of enemy it is
            'x': self.x,
            'y': self.y,
            'health': self.health,
            'max_health': self.max_health,
            'facing_right': self.facing_right,
            'anim_type': self.current_animation_type,
            'anim_frame': self.current_frame_index,
            'anim_finished': self.animation_finished,
            'is_dead': self.is_dead,
            'is_invulnerable': self.is_invulnerable,
            'is_attacking': self.is_attacking,
            'dialogue_text': self.dialogue_text, # Send dialogue too
            'dialogue_timer': self.dialogue_timer
        }

    # <<< NETWORK: Method to update state from network data (CLIENT SIDE) >>>
    def apply_network_state(self, state_data):
        """Updates the enemy's attributes based on received network data."""
        # Directly update core attributes
        self.x = state_data.get('x', self.x)
        self.y = state_data.get('y', self.y)
        self.health = state_data.get('health', self.health)
        self.max_health = state_data.get('max_health', self.max_health)
        self.facing_right = state_data.get('facing_right', self.facing_right)
        self.is_dead = state_data.get('is_dead', self.is_dead)
        self.is_invulnerable = state_data.get('is_invulnerable', self.is_invulnerable)
        self.is_attacking = state_data.get('is_attacking', self.is_attacking)
        self.dialogue_text = state_data.get('dialogue_text', self.dialogue_text)
        self.dialogue_timer = state_data.get('dialogue_timer', self.dialogue_timer)

        # Update animation state carefully
        new_anim_type = state_data.get('anim_type', self.current_animation_type)
        new_anim_frame = state_data.get('anim_frame', self.current_frame_index)
        new_anim_finished = state_data.get('anim_finished', self.animation_finished)

        if new_anim_type != self.current_animation_type:
            self.current_animation_type = new_anim_type
            self.current_frame_index = new_anim_frame # Use server's frame on change
        elif self.current_animation_type == new_anim_type:
             self.current_frame_index = new_anim_frame # Sync frame

        self.animation_finished = new_anim_finished

        # Update rect based on new position
        self.rect.center = (int(self.x), int(self.y))