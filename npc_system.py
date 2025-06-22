import pygame
import random
import math

# Fallback values if modules not found directly (e.g., running standalone)
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# --- NPC Constants ---
NPC_COLOR = (0, 150, 250) # Blueish color
NPC_RADIUS = 12
NPC_SPEED = 1.5
NPC_WANDER_RADIUS = 150
NPC_WANDER_TIME_MIN = 3.0
NPC_WANDER_TIME_MAX = 7.0
NPC_INTERACTION_RANGE = 50 # How close player needs to be to interact
NPC_INTERACTION_RANGE_SQ = NPC_INTERACTION_RANGE * NPC_INTERACTION_RANGE # Squared for efficiency
NPC_DIALOGUE_DURATION = 4.0 # Seconds each line stays up

# --- Font Constants ---
try:
    # Initialize font module if not already done (safe to call multiple times)
    pygame.font.init()
    UI_FONT_NPCS = pygame.font.SysFont(None, 24) # Font for NPC name/dialogue
    DIALOGUE_FONT_NPCS = pygame.font.SysFont(None, 28) # Slightly larger for dialogue box
except Exception as e:
    print(f"Warning: Could not load default system font for NPCs: {e}")
    UI_FONT_NPCS = None
    DIALOGUE_FONT_NPCS = None

DIALOGUE_TEXT_COLOR = (255, 255, 255) # White text
DIALOGUE_BG_COLOR = (30, 30, 80, 200) # Semi-transparent dark blue background
DIALOGUE_BOX_PADDING = 15
DIALOGUE_BOX_WIDTH_RATIO = 0.7 # Percentage of screen width
DIALOGUE_BOX_HEIGHT = 100 # Fixed height for simplicity
DIALOGUE_BOX_Y_POS = SCREEN_HEIGHT - DIALOGUE_BOX_HEIGHT - 20 # Position near bottom

# --- NPC Class ---
class NPC:
    # <<< NETWORK: Add class counter for unique IDs >>>
    _npc_id_counter = 0

    def __init__(self, x, y, name="Villager", npc_type="Villager", dialogue=None):
        # <<< NETWORK: Assign unique ID >>>
        self.id = NPC._npc_id_counter
        NPC._npc_id_counter += 1
        self.npc_type = npc_type # Store type (e.g., "Villager", "Merchant")

        self.x = x; self.y = y; self.spawn_x = x; self.spawn_y = y
        self.radius = NPC_RADIUS; self.speed = NPC_SPEED; self.color = NPC_COLOR
        self.rect = pygame.Rect(x - self.radius, y - self.radius, self.radius * 2, self.radius * 2)
        self.name = f"{name} #{self.id}" # Add ID to name for uniqueness
        self.dialogue = dialogue if dialogue else [f"Hello there, traveler! I'm {self.name}."]

        # State and Movement
        self.state = 'idle' # idle, wander, talking
        self.target_position = None
        self.wander_timer = random.uniform(NPC_WANDER_TIME_MIN, NPC_WANDER_TIME_MAX)
        self.facing_direction = pygame.math.Vector2(0, 1) # Start facing down

        # Dialogue State
        self.dialogue_active = False
        self.current_dialogue_index = 0
        self.dialogue_timer = 0.0
        # <<< NETWORK: Store ID of interacting player (server-side use primarily) >>>
        self.talking_to_player_id = None

    def update_behavior(self, dt, colliders_nearby):
        """ (Server Only) Updates NPC state machine and movement based on behavior. """
        if self.state == 'talking':
            # Don't wander or move while talking
            self.wander_timer = random.uniform(NPC_WANDER_TIME_MIN, NPC_WANDER_TIME_MAX) # Reset wander timer
            return

        self.wander_timer -= dt

        # --- State Transitions ---
        if self.state == 'idle':
            if self.wander_timer <= 0:
                # Time to wander
                angle = random.uniform(0, 2 * math.pi)
                dist = random.uniform(0, NPC_WANDER_RADIUS)
                # Keep wander target near spawn
                target_x = self.spawn_x + math.cos(angle) * dist
                target_y = self.spawn_y + math.sin(angle) * dist
                # Basic bounds check (replace with actual world bounds if needed)
                target_x = max(self.radius, min(target_x, SCREEN_WIDTH - self.radius)) # Use world bounds later
                target_y = max(self.radius, min(target_y, SCREEN_HEIGHT - self.radius))# Use world bounds later
                self.target_position = pygame.math.Vector2(target_x, target_y)
                self.state = 'wander'
                # print(f"NPC {self.id} starting wander to {self.target_position}") # Debug

        elif self.state == 'wander':
            if self.target_position:
                direction = self.target_position - pygame.math.Vector2(self.x, self.y)
                dist_to_target = direction.length()

                if dist_to_target < self.speed * dt * 60 * 0.5 : # Close enough to target
                    # print(f"NPC {self.id} reached wander target.") # Debug
                    self.state = 'idle'
                    self.target_position = None
                    self.wander_timer = random.uniform(NPC_WANDER_TIME_MIN, NPC_WANDER_TIME_MAX)
                else:
                    # Move towards target
                    move_vector = direction.normalize() * self.speed * dt * 60 # Use FPS scaling
                    self.facing_direction = direction.normalize() # Update facing direction

                    # --- Basic Collision Avoidance (Server Only) ---
                    potential_move_x = self.x + move_vector.x
                    potential_move_y = self.y + move_vector.y
                    temp_rect_x = self.rect.copy()
                    temp_rect_x.centerx = int(potential_move_x)
                    collided_x = False
                    for obs in colliders_nearby:
                         if temp_rect_x.colliderect(obs):
                              collided_x = True; break

                    temp_rect_y = self.rect.copy()
                    temp_rect_y.centery = int(potential_move_y)
                    collided_y = False
                    for obs in colliders_nearby:
                         if temp_rect_y.colliderect(obs):
                              collided_y = True; break

                    # Apply movement only if no collision on that axis
                    if not collided_x: self.x = potential_move_x
                    if not collided_y: self.y = potential_move_y

                    self.rect.center = (int(self.x), int(self.y))

            else: # No target position while wandering? Go idle.
                self.state = 'idle'
                self.wander_timer = random.uniform(NPC_WANDER_TIME_MIN, NPC_WANDER_TIME_MAX)

        # World boundary clamp (use effective world dimensions from main game)
        # self.x = max(self.radius, min(self.x, world_width - self.radius))
        # self.y = max(self.radius, min(self.y, world_height - self.radius))
        # self.rect.center = (int(self.x), int(self.y))


    def update_dialogue(self, dt):
        """(Server Only) Manages the progression and timeout of dialogue."""
        if self.dialogue_active:
            self.dialogue_timer -= dt
            if self.dialogue_timer <= 0:
                # Advance to next line or end dialogue
                self.current_dialogue_index += 1
                if self.current_dialogue_index >= len(self.dialogue):
                    # End of dialogue
                    self.dialogue_active = False
                    self.current_dialogue_index = 0
                    self.state = 'idle' # Revert state after talking
                    self.talking_to_player_id = None # Clear interacting player
                    # print(f"NPC {self.id} finished dialogue.") # Debug
                else:
                    # Set timer for the next line
                    self.dialogue_timer = NPC_DIALOGUE_DURATION

    # <<< NETWORK: Modified to store player ID >>>
    def interact(self, interacting_player_id):
        """(Server Only) Called when a player interacts with this NPC."""
        if not self.dialogue_active: # Start new dialogue if not already talking
            print(f"NPC {self.id} interacted with by Player {interacting_player_id}") # Debug
            self.state = 'talking'
            self.dialogue_active = True
            self.current_dialogue_index = 0
            self.dialogue_timer = NPC_DIALOGUE_DURATION
            self.talking_to_player_id = interacting_player_id
            # Make NPC face the player? (Needs player position - manager handles this)
        # If already talking, could potentially advance dialogue on interact press?
        # else: # Already talking, advance dialogue?
        #    self.dialogue_timer = 0 # Force advance on next update_dialogue tick

    def draw(self, surface, camera_apply_point_func):
        """(Client & Host) Draws the NPC."""
        screen_pos = camera_apply_point_func(self.x, self.y)

        # Draw NPC body (simple circle for now)
        pygame.draw.circle(surface, self.color, screen_pos, self.radius)
        pygame.draw.circle(surface, (0,0,0), screen_pos, self.radius, 1) # Outline

        # Draw name tag above
        if UI_FONT_NPCS:
            name_surf = UI_FONT_NPCS.render(self.name, True, (220, 220, 255))
            name_rect = name_surf.get_rect(centerx=screen_pos[0], bottom=screen_pos[1] - self.radius - 3)
            surface.blit(name_surf, name_rect)

    def get_current_dialogue_line(self):
        """Returns the current dialogue line if active."""
        if self.dialogue_active and 0 <= self.current_dialogue_index < len(self.dialogue):
            return self.dialogue[self.current_dialogue_index]
        return None

    # <<< NETWORK: Method to get serializable state >>>
    def get_network_state(self):
        """Returns a dictionary of the NPC's state for network transmission."""
        return {
            'id': self.id,
            'type': self.npc_type,
            'x': self.x,
            'y': self.y,
            'name': self.name, # Send name in case it's dynamic? Or client can derive? Send for now.
            'state': self.state, # Client uses this for visual cues if needed
            'dialogue_active': self.dialogue_active,
            'current_dialogue_index': self.current_dialogue_index,
            # 'facing_direction': [self.facing_direction.x, self.facing_direction.y], # Optional
            # Send dialogue text itself? Only needed if dynamic. Assume client has it for now.
            'talking_to_player_id': self.talking_to_player_id, # Client might use this to highlight speaker?
        }

    # <<< NETWORK: Method to update state from network data (CLIENT SIDE) >>>
    def apply_network_state(self, state_data):
        """(Client Only) Updates the NPC's attributes based on received network data."""
        # Directly update core visual attributes
        self.x = state_data.get('x', self.x)
        self.y = state_data.get('y', self.y)
        self.name = state_data.get('name', self.name) # Update name if sent
        self.state = state_data.get('state', self.state) # Update behavioral state

        # Update dialogue status for drawing
        self.dialogue_active = state_data.get('dialogue_active', self.dialogue_active)
        self.current_dialogue_index = state_data.get('current_dialogue_index', self.current_dialogue_index)
        self.talking_to_player_id = state_data.get('talking_to_player_id', self.talking_to_player_id)

        # Update facing direction if sent
        # facing = state_data.get('facing_direction')
        # if facing: self.facing_direction = pygame.math.Vector2(facing)

        # Update rect based on new position
        self.rect.center = (int(self.x), int(self.y))


# --- NPC Manager Class (Modified for Networking) ---
class NPCManager:
    # <<< NETWORK: Added network_players and is_host >>>
    def __init__(self, world_data, screen_height, screen_width, network_players, is_host):
        self.world_data = world_data # Might contain spawn locations, etc.
        self.screen_height = screen_height
        self.screen_width = screen_width
        self.network_players = network_players # Reference to the shared player dictionary
        self.is_host = is_host # Flag to determine server/client logic

        # <<< NETWORK: Use different collections for host/client >>>
        if self.is_host:
            self.npcs = [] # Server: Authoritative list of NPC objects
            NPC._npc_id_counter = 0 # Reset counter on server start
        else:
            self.client_npcs = {} # Client: Dictionary {id: npc_obj} synchronized from server

        self.active_dialogue_npc_id = None # Track which NPC's dialogue is showing (globally for now)


    def spawn_npcs_in_overworld(self, kingdom_center_x, kingdom_center_y, is_point_in_polygon_func):
        """(Server Only) Spawns NPCs, e.g., within a kingdom boundary."""
        if not self.is_host: return # Only server spawns

        print("[SERVER] Spawning NPCs in Overworld...")
        num_npcs = 5 # Example number
        spawn_radius = 150 # Spawn within this radius of the kingdom center

        # Example: Basic Villager dialogue
        dialogue_options = [
            ["The weather's been strange lately.", "Seen any adventurers around here?"],
            ["Welcome to our village!", "Watch out for the monsters in the forest."],
            ["Need anything?", "Just enjoying the day."],
            ["Did you hear the news?", "Something about the old ruins..."],
            ["Ah, another traveler.", "Be safe out there."]
        ]

        spawned_count = 0
        attempts = 0
        max_attempts = num_npcs * 10

        while spawned_count < num_npcs and attempts < max_attempts:
            attempts += 1
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(0, spawn_radius)
            spawn_x = kingdom_center_x + math.cos(angle) * dist
            spawn_y = kingdom_center_y + math.sin(angle) * dist

            # Optional: Check if point is valid (e.g., inside polygon, not in wall)
            # if is_point_in_polygon_func((spawn_x, spawn_y), KINGDOM_POLY_POINTS): # If needed

            npc_dialogue = random.choice(dialogue_options)
            new_npc = NPC(spawn_x, spawn_y, dialogue=npc_dialogue)
            self.npcs.append(new_npc)
            spawned_count += 1
            print(f"[SERVER] Spawned NPC {new_npc.id} at ({int(spawn_x)}, {int(spawn_y)})")

        print(f"[SERVER] Finished spawning {spawned_count} NPCs.")


    def spawn_npcs_in_dungeon(self):
         """(Server Only) Spawns NPCs in the dungeon."""
         if not self.is_host: return
         # Add dungeon-specific spawning logic here if needed
         print("[SERVER] NPC Dungeon spawning not implemented yet.")
         pass


    def update(self, dt, collision_quadtree=None):
        """(Server Only) Updates behavior and dialogue for all managed NPCs."""
        if not self.is_host: return # Only server updates logic

        for npc in self.npcs:
            # Get colliders near the NPC for its behavior update
            colliders_nearby = []
            if collision_quadtree:
                 query_range = npc.rect.inflate(npc.speed * 2 + 32, npc.speed * 2 + 32)
                 colliders_nearby = collision_quadtree.query(query_range)

            npc.update_behavior(dt, colliders_nearby)
            npc.update_dialogue(dt)

            # Check if this NPC's dialogue should be the active one shown
            if npc.dialogue_active:
                self.active_dialogue_npc_id = npc.id
            elif self.active_dialogue_npc_id == npc.id and not npc.dialogue_active:
                 # If this NPC was the active one but no longer is, clear it
                 self.active_dialogue_npc_id = None

    # <<< NETWORK: Takes the specific player object >>>
    def handle_interaction(self, player):
        """(Server Only) Handles a player's request to interact with nearby NPCs."""
        if not self.is_host or not player: return # Only server handles, needs valid player

        closest_npc = None
        min_dist_sq = NPC_INTERACTION_RANGE_SQ # Use squared distance

        for npc in self.npcs:
            dist_sq = (npc.x - player.x)**2 + (npc.y - player.y)**2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                closest_npc = npc

        if closest_npc:
            # Player is close enough to the closest NPC, trigger interaction
            closest_npc.interact(player.player_id)
            # Optional: Make NPC face player
            # direction_to_player = pygame.math.Vector2(player.x, player.y) - pygame.math.Vector2(closest_npc.x, closest_npc.y)
            # if direction_to_player.length_squared() > 0:
            #     closest_npc.facing_direction = direction_to_player.normalize()
            # print(f"Interaction handled between Player {player.player_id} and NPC {closest_npc.id}") # Debug
        # else:
            # print(f"Player {player.player_id} tried to interact, but no NPC in range.") # Debug


    def draw(self, surface, camera_apply_point_func):
        """(Client & Host) Draws all NPCs."""
        # <<< NETWORK: Choose correct list based on host/client >>>
        npcs_to_draw = self.npcs if self.is_host else self.client_npcs.values()

        for npc in npcs_to_draw:
            # Add basic distance culling?
            # screen_rect = surface.get_rect()
            # screen_pos = camera_apply_point_func(npc.x, npc.y)
            # if screen_rect.collidepoint(screen_pos): # Very basic culling
            npc.draw(surface, camera_apply_point_func)


    def draw_dialogue(self, surface):
        """(Client & Host) Draws the dialogue box for the currently active NPC."""
        npc_to_show = None
        # <<< NETWORK: Find the active NPC in the correct collection >>>
        if self.active_dialogue_npc_id is not None:
            if self.is_host:
                for npc in self.npcs:
                    if npc.id == self.active_dialogue_npc_id and npc.dialogue_active:
                        npc_to_show = npc; break
            else: # Client
                npc_to_show = self.client_npcs.get(self.active_dialogue_npc_id)
                # Ensure the client object also thinks dialogue is active
                if npc_to_show and not npc_to_show.dialogue_active:
                     npc_to_show = None # Mismatch between manager active ID and object state

        if npc_to_show and DIALOGUE_FONT_NPCS:
            line = npc_to_show.get_current_dialogue_line()
            if line:
                # --- Draw Dialogue Box Background ---
                box_width = self.screen_width * DIALOGUE_BOX_WIDTH_RATIO
                box_x = (self.screen_width - box_width) / 2
                dialogue_rect = pygame.Rect(box_x, DIALOGUE_BOX_Y_POS, box_width, DIALOGUE_BOX_HEIGHT)

                # Use a temporary surface for transparency
                temp_surface = pygame.Surface(dialogue_rect.size, pygame.SRCALPHA)
                pygame.draw.rect(temp_surface, DIALOGUE_BG_COLOR, temp_surface.get_rect(), border_radius=8)
                surface.blit(temp_surface, dialogue_rect.topleft)

                # Draw border
                pygame.draw.rect(surface, (200, 200, 220), dialogue_rect, 2, border_radius=8)

                # --- Draw Text ---
                # Basic word wrapping (replace with a more robust solution if needed)
                words = line.split(' ')
                lines_to_render = []
                current_line = ""
                text_area_width = dialogue_rect.width - DIALOGUE_BOX_PADDING * 2
                line_height = DIALOGUE_FONT_NPCS.get_linesize()
                max_lines = (dialogue_rect.height - DIALOGUE_BOX_PADDING * 2) // line_height

                for word in words:
                    test_line = current_line + word + " "
                    test_surf = DIALOGUE_FONT_NPCS.render(test_line, True, DIALOGUE_TEXT_COLOR)
                    if test_surf.get_width() <= text_area_width:
                        current_line = test_line
                    else:
                        lines_to_render.append(current_line)
                        current_line = word + " "
                lines_to_render.append(current_line) # Add the last line

                # Render the lines
                draw_y = dialogue_rect.top + DIALOGUE_BOX_PADDING
                for i, text_line in enumerate(lines_to_render):
                     if i >= max_lines: break # Stop if too many lines for the box
                     line_surf = DIALOGUE_FONT_NPCS.render(text_line.strip(), True, DIALOGUE_TEXT_COLOR)
                     line_rect = line_surf.get_rect(topleft=(dialogue_rect.left + DIALOGUE_BOX_PADDING, draw_y))
                     surface.blit(line_surf, line_rect)
                     draw_y += line_height


    # <<< NETWORK: Methods for state synchronization >>>
    def get_all_npcs_network_state(self):
        """(Server Only) Returns a dictionary of states for all active NPCs."""
        if not self.is_host: return {}
        return {npc.id: npc.get_network_state() for npc in self.npcs}

    def apply_npc_network_state(self, npc_states_dict):
        """(Client Only) Updates the client's NPC list based on server data."""
        if self.is_host: return # Server doesn't apply state to itself

        server_ids = set(npc_states_dict.keys())
        client_ids = set(self.client_npcs.keys())

        # Add/Update NPCs
        for npc_id, state_data in npc_states_dict.items():
            if npc_id in self.client_npcs:
                # Update existing NPC
                self.client_npcs[npc_id].apply_network_state(state_data)
            else:
                # New NPC encountered, create it locally
                npc_type = state_data.get('type', 'Villager') # Get type, default if missing
                # In a more complex system, you might look up NPC class based on type
                try:
                    # For now, assume all NPCs are base NPC class
                    # We need dialogue from somewhere - cannot easily sync dynamic dialogue state this way
                    # Simplification: Client NPCs get default dialogue or none
                    new_npc = NPC(state_data['x'], state_data['y'], name=state_data.get('name','NPC'), npc_type=npc_type, dialogue=["..."])
                    # Override ID and apply full state
                    new_npc.id = npc_id # Ensure correct ID
                    new_npc.apply_network_state(state_data) # Apply rest of state
                    self.client_npcs[npc_id] = new_npc
                    # print(f"[CLIENT] Spawned NPC {npc_id} ({npc_type})") # Debug
                except Exception as e:
                    print(f"[CLIENT] Error creating new NPC {npc_id} of type {npc_type}: {e}")

        # Remove NPCs that are no longer in the server's state
        removed_ids = client_ids - server_ids
        for npc_id in removed_ids:
            if npc_id in self.client_npcs:
                # print(f"[CLIENT] Removing NPC {npc_id}") # Debug
                # Clear active dialogue if the removed NPC was speaking
                if self.active_dialogue_npc_id == npc_id:
                    self.active_dialogue_npc_id = None
                del self.client_npcs[npc_id]

        # --- Update active dialogue ID based on received states ---
        # Find if *any* received NPC state has dialogue_active = True
        self.active_dialogue_npc_id = None # Reset first
        for npc_id, state_data in npc_states_dict.items():
             if state_data.get('dialogue_active', False):
                  self.active_dialogue_npc_id = npc_id
                  break # Assume only one can be active globally
