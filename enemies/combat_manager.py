import random

import enemies.player as player_module
from combat_mech import PLAYER_ATTACK_POWER, PLAYER_ATTACK_RANGE

from enemies.enemy_base import Enemy
from world_struct import *

from NETconfig import is_host

# Import enemy types, constants
from .sword_orc import Sword_Orc# Import other enemy types as needed
from .stat_constants import *

class CombatManager:
    def __init__(self, world_data, collision_quadtree, is_point_in_polygon_func,
                 all_enemy_animations, network_players_dict):
        """
        Manages combat interactions, enemy spawning, updates, and drawing.

        Args:
            world_data (dict): Dictionary containing world information (polygons, dimensions, dungeon data).
            collision_quadtree: Quadtree instance for spatial queries of colliders.
            is_point_in_polygon_func: Function to check point-in-polygon containment.
            all_enemy_animations (dict): Nested dictionary mapping enemy type names to their animation data
                                         (e.g., {"Sword_Orc": {"idle": [...], "walk": [...], ... "dims": (w,h)}}).
        """
        self.world_data = world_data
        self.quadtree = collision_quadtree
        self.is_point_in_polygon = is_point_in_polygon_func
        self.enemies = [] # List to hold active enemy instances
        
        self.client_enemies = {} # <<< NETWORK: Client: Dictionary of Enemy objects {enemy_id: enemy_obj}
        self.network_players = network_players_dict # Reference to the shared player dictionary

        self.enemy_animations = all_enemy_animations
        # Map enemy type names (strings) to their actual class objects
        self.enemy_classes = {
             "Sword_Orc": Sword_Orc,
             # "Goblin": Goblin, # Add mappings for other imported enemy classes
             # "Skeleton": Skeleton,
        }
        self.available_enemy_types = list(self.enemy_classes.keys())
        if not self.available_enemy_types:
             print("WARNING: No enemy types defined/mapped in CombatManager!")

        # Reset enemy ID counter at initialization (server side)
        Enemy._enemy_id_counter = 0

    def spawn_enemies_in_overworld(self, count):
        """(Server Only) Spawns enemies in the overworld."""
        print(f"[SERVER] Spawning {count} enemies in Overworld...")
        if not self.available_enemy_types: return

        spawned_count = 0
        attempts = 0
        max_attempts = count * 20
        forest_poly = self.world_data.get("forest_poly_points")
        kingdom_poly = self.world_data.get("kingdom_poly_points")
        world_w = self.world_data.get("WORLD_WIDTH", 20000)
        world_h = self.world_data.get("WORLD_HEIGHT", 20000)

        while spawned_count < count and attempts < max_attempts:
            attempts += 1
            spawn_x = random.randint(0, world_w)
            spawn_y = random.randint(0, world_h)
            spawn_point = (spawn_x, spawn_y)

            # Check validity (e.g., outside kingdom)
            in_kingdom = kingdom_poly and self.is_point_in_polygon(spawn_point, kingdom_poly)
            if not in_kingdom:
                enemy_type_name = random.choice(self.available_enemy_types)
                EnemyClass = self.enemy_classes.get(enemy_type_name)
                animations = self.enemy_animations.get(enemy_type_name)

                if EnemyClass and animations:
                    try:
                        new_enemy = EnemyClass(spawn_x, spawn_y,
                                               animations['idle'], animations['walk'],
                                               animations['attack'], animations['hurt'],
                                               animations['death'], animations['dims'])
                        self.enemies.append(new_enemy) # Add to server list
                        spawned_count += 1
                    except KeyError as e:
                        print(f"[SERVER] ERROR: Missing animation key '{e}' for {enemy_type_name}.")
                    except Exception as e:
                         print(f"[SERVER] ERROR: Failed to instantiate {enemy_type_name}: {e}")
                else:
                    print(f"[SERVER] Warning: Could not find class or animations for {enemy_type_name}.")

        print(f"[SERVER] Successfully spawned {spawned_count} enemies in Overworld.")


    def spawn_enemies_in_dungeon(self, count):
        """(Server Only) Spawns enemies in the dungeon."""
        print(f"[SERVER] Spawning {count} enemies in Dungeon...")
        if not self.available_enemy_types: return

        spawned_count = 0
        attempts = 0
        max_attempts = count * 20
        dungeon_rooms = self.world_data.get("dungeon_rooms_grid", [])
        dungeon_grid = self.world_data.get("dungeon_grid")
        TILE_FLOOR = TILE_FLOOR # Get from world_struct
        DUNGEON_TILE_SIZE = DUNGEON_TILE_SIZE

        if not dungeon_rooms or not dungeon_grid:
            print("[SERVER] Warning: Cannot spawn dungeon enemies, grid/rooms missing.")
            return

        while spawned_count < count and attempts < max_attempts:
             attempts += 1
             try:
                 room = random.choice(dungeon_rooms)
                 grid_x = random.randint(room.left, room.right - 1)
                 grid_y = random.randint(room.top, room.bottom - 1)

                 if 0 <= grid_y < len(dungeon_grid) and 0 <= grid_x < len(dungeon_grid[0]) and dungeon_grid[grid_y][grid_x] == TILE_FLOOR:
                     spawn_x = grid_x * DUNGEON_TILE_SIZE + DUNGEON_TILE_SIZE // 2
                     spawn_y = grid_y * DUNGEON_TILE_SIZE + DUNGEON_TILE_SIZE // 2

                     enemy_type_name = random.choice(self.available_enemy_types)
                     EnemyClass = self.enemy_classes.get(enemy_type_name)
                     animations = self.enemy_animations.get(enemy_type_name)

                     if EnemyClass and animations:
                         try:
                             new_enemy = EnemyClass(spawn_x, spawn_y,
                                                  animations['idle'], animations['walk'],
                                                  animations['attack'], animations['hurt'],
                                                  animations['death'], animations['dims'])
                             self.enemies.append(new_enemy) # Add to server list
                             spawned_count += 1
                         except KeyError as e:
                              print(f"[SERVER] ERROR: Missing animation key '{e}' for {enemy_type_name}.")
                         except Exception as e:
                             print(f"[SERVER] ERROR: Failed to instantiate {enemy_type_name}: {e}")
                     else:
                        print(f"[SERVER] Warning: Could not find class/animations for {enemy_type_name}.")

             except IndexError: continue
             except ValueError: continue

        print(f"[SERVER] Successfully spawned {spawned_count} enemies in Dungeon.")

    # <<< NETWORK: handle_player_attack takes the specific player object >>>
    def handle_player_attack(self, player):
        """(Server Only) Processes an attack action from a specific player."""
        if player.is_dead or not player.is_attacking:
            return

        # Calculate attack hitbox based on player's facing direction
        attack_center_offset = player.last_direction * (PLAYER_ATTACK_RANGE / 2)
        attack_center_x = player.x + attack_center_offset.x
        attack_center_y = player.y + attack_center_offset.y
        # Use a squared range for efficient distance checking
        attack_range_sq = (PLAYER_ATTACK_RANGE * 0.8)**2 # Adjust hitbox size as needed

        enemies_hit_count = 0
        for enemy in self.enemies:
            if enemy.is_dead: continue

            # Check distance from attack center to enemy center
            dist_sq = (enemy.x - attack_center_x)**2 + (enemy.y - attack_center_y)**2
            # Add enemy radius to check for overlap
            if dist_sq < attack_range_sq + (enemy.radius**2):
                # Check Enemy Agility (Dodge)
                if random.random() < enemy.agility:
                    # print(f"{enemy.name} ({enemy.id}) dodged Player {player.player_id} attack!")
                    continue # Enemy dodged

                # Apply damage (take_damage handles defense)
                damage_dealt = enemy.take_damage(PLAYER_ATTACK_POWER)
                if damage_dealt > 0:
                     enemies_hit_count += 1
                # Optional: Add knockback effect here
        
        # --- 2. Check for hits against OTHER PLAYERS (PvP) ---
        players_hit_count = 0
        # Iterate through all players known to the server (including the attacker)
        for target_player_id, target_player in self.network_players.items():
            # Skip the attacking player and dead players
            if target_player_id == player.player_id or target_player.is_dead:
                continue

            # Check distance from attack center to the target player's center
            dist_sq = (target_player.x - attack_center_x)**2 + (target_player.y - attack_center_y)**2
            # Add target player radius for overlap check
            if dist_sq < attack_range_sq + (target_player.radius**2):
                # Check Target Player Agility (Dodge)
                if random.random() < target_player.agility:
                    print(f"Player {target_player_id} dodged Player {player.player_id}'s attack!")
                    continue # Target player dodged

                # Apply damage to the target player
                print(f"PVP HIT! Player {player.player_id} hits Player {target_player_id}") # Debug
                damage_dealt = target_player.take_damage(PLAYER_ATTACK_POWER)
                if damage_dealt > 0:
                    players_hit_count += 1

        # print(f"Player {player.player_id} attack hit {enemies_hit_count} enemies.") # Debug


    # <<< NETWORK: handle_enemy_attack takes the specific player object being attacked >>>
    def handle_enemy_attack(self, enemy, target_player):
        """ (Server Only) Called when an enemy's attack animation hits its target player. """
        if enemy.is_dead or target_player.is_dead:
             return

        # Double-check range at the moment of the hit frame (optional, could rely on anim start range)
        dist_sq = (target_player.x - enemy.x)**2 + (target_player.y - enemy.y)**2
        effective_attack_range_sq = enemy.attack_range * enemy.attack_range # Use squared range

        if dist_sq < effective_attack_range_sq:
            # Check Player Agility (Dodge)
            if random.random() < target_player.agility:
                # print(f"Player {target_player.player_id} dodged {enemy.name}'s attack!")
                # Optionally: trigger a "miss" effect/sound
                return # Player dodged

            # Apply damage to the specific player (player.take_damage handles defense)
            # print(f"HIT! {enemy.name} ({enemy.id}) attacks Player {target_player.player_id}.") # Debug
            target_player.take_damage(enemy.attack_power)
        # else:
             # Attack missed because target moved out of range after animation started


    def update(self, network_players_dict, dt, collision_quadtree, game_state):
        """(Server Only) Updates all enemies."""
        if not network_players_dict: return # Don't update if no players

        enemies_to_remove = []
        for enemy in self.enemies:
            # Get nearby colliders for this enemy
            potential_colliders = []
            if collision_quadtree:
                 query_range = enemy.rect.inflate(enemy.speed * 2 + 32, enemy.speed * 2 + 32)
                 potential_colliders = collision_quadtree.query(query_range)

            # Enemy update logic (targeting, movement, animation)
            # Pass the dictionary of players to the enemy's update method
            reached_hit_frame = enemy.update(network_players_dict, dt, potential_colliders, game_state, collision_quadtree, self.is_point_in_polygon)

            # If the update indicated the attack hit frame was reached, process the attack
            if reached_hit_frame and enemy.target_player:
                # Pass the specific enemy and its target player to the handler
                self.handle_enemy_attack(enemy, enemy.target_player)

            # Check if enemy is dead and animation finished
            if enemy.is_dead and enemy.animation_finished:
                enemies_to_remove.append(enemy)

        # Remove dead enemies from the main list
        if enemies_to_remove:
             # print(f"[SERVER] Removing {len(enemies_to_remove)} defeated enemies.")
             for enemy in enemies_to_remove:
                 self.enemies.remove(enemy)
             # Optional: Send message to clients about enemy removal? State update handles disappearance.


    def draw(self, surface, camera_apply_point_func):
        """(Client & Host) Draws enemies based on received state or local state."""
        # Determine which list of enemies to draw from
        # Server draws its authoritative list, Client draws its synchronized list
        enemies_to_draw = self.enemies if is_host else list(self.client_enemies.values())

        # Simple distance culling could be added here if needed

        for enemy in enemies_to_draw:
             # Enemy object's draw method handles animation state
             enemy.draw(surface, camera_apply_point_func)

    # <<< NETWORK: Methods for state synchronization >>>
    def get_all_enemies_network_state(self):
        states = {}
        for enemy in self.enemies:
            st = enemy.get_network_state()
            # inject the class name so the client knows what to instantiate:
            st['type'] = enemy.__class__.__name__
            states[enemy.id] = st
        return states

    def apply_enemy_network_state(self, enemy_states_dict):
        """(Client Only) Updates the client's enemy list based on server data."""
        if is_host: return # Server doesn't apply state to itself

        server_ids = set(enemy_states_dict.keys())
        client_ids = set(self.client_enemies.keys())

        # Add/Update enemies
        for enemy_id, state_data in enemy_states_dict.items():
            if enemy_id in self.client_enemies:
                # Update existing enemy
                self.client_enemies[enemy_id].apply_network_state(state_data)
            else:
                # New enemy encountered, create it locally
                enemy_type = state_data.get('type')
                EnemyClass = self.enemy_classes.get(enemy_type)
                animations = self.enemy_animations.get(enemy_type)

                if EnemyClass and animations:
                    try:
                        new_enemy = EnemyClass(state_data['x'], state_data['y'],
                                               animations['idle'], animations['walk'],
                                               animations['attack'], animations['hurt'],
                                               animations['death'], animations['dims'])
                        # Override ID and apply full state
                        new_enemy.id = enemy_id # Ensure correct ID
                        new_enemy.apply_network_state(state_data)
                        self.client_enemies[enemy_id] = new_enemy
                        # print(f"[CLIENT] Spawned enemy {enemy_id} ({enemy_type})") # Debug
                    except Exception as e:
                        print(f"[CLIENT] Error creating new enemy {enemy_id} of type {enemy_type}: {e}")
                else:
                    print(f"[CLIENT] Warning: Cannot create enemy {enemy_id}, unknown type '{enemy_type}' or missing animations.")

        # Remove enemies that are no longer in the server's state
        removed_ids = client_ids - server_ids
        for enemy_id in removed_ids:
            if enemy_id in self.client_enemies:
                # print(f"[CLIENT] Removing enemy {enemy_id}") # Debug
                del self.client_enemies[enemy_id]