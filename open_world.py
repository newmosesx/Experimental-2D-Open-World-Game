import pygame
import sys
import random

# Networking
import socket
import threading
import pickle
import select

from world_structures import drawing
from NETconfig import *

# Import other game modules
import world_struct as world_struct_stable
import combat_mech as combat_mech_stable

# Import newly created modules
import asset.assets as assets
import open_world_dir.loading as loading
import enemies.player as player_module # Used alias to avoid conflict with player instance variable
import open_world_dir.camera_map as camera_map
import open_world_dir.ui as ui

# --- Core Constants ---
SCREEN_WIDTH = world_struct_stable.SCREEN_WIDTH
SCREEN_HEIGHT = world_struct_stable.SCREEN_HEIGHT
PLAYER_RADIUS = world_struct_stable.PLAYER_RADIUS # Keep radius for collision/initial rect
PLAYER_SPEED = world_struct_stable.PLAYER_SPEED # Keep speed for player creation
PLAYER_COLOR = (220, 0, 0) # Fallback color
FPS = 60

# --- Game State ---
game_state = "overworld" # Start in the overworld
# game_state = "dungeon"

show_map = False

# --- Network Helper Functions ---
def send_data(sock, data):
    """Sends pickled data prefixed with its size."""
    try:
        # Serialize the data object into bytes
        pickled_data = pickle.dumps(data)
        # Create a fixed-size header containing the length of the data
        header = f"{len(pickled_data):<{HEADER_SIZE}}".encode('utf-8')
        # Send the header followed by the pickled data
        sock.sendall(header + pickled_data)
        return True
    except (socket.error, pickle.PicklingError, BrokenPipeError, ConnectionResetError) as e:
        # Handle common network sending errors
        print(f"NETWORK SEND ERROR: {e}")
        return False # Indicate failure

def receive_data(sock):
    """Receives data prefixed with its size."""
    full_msg = b''
    new_msg = True
    expected_msg_len = 0
    while True:
        try:
            # 1. Receive the header (fixed size)
            if new_msg:
                header = sock.recv(HEADER_SIZE)
                if not header:
                    print("NETWORK RECV ERROR: Connection closed (header).")
                    return None # Connection closed
                try:
                    # Decode the header to determine the expected message length
                    expected_msg_len = int(header.decode('utf-8').strip())
                    new_msg = False
                    full_msg = b'' # Reset message buffer
                except ValueError:
                    print(f"NETWORK RECV ERROR: Invalid header received: {header}")
                    return None

            # 2. Receive the main message chunk by chunk
            # Receive in chunks to handle large data packets
            chunk = sock.recv(min(4096, expected_msg_len - len(full_msg)))
            if not chunk:
                print("NETWORK RECV ERROR: Connection closed (data).")
                return None # Connection closed

            full_msg += chunk

            # 3. Check if the full message is received
            if len(full_msg) == expected_msg_len:
                # 4. Unpickle the complete message
                try:
                    # Deserialize the bytes back into a Python object
                    data = pickle.loads(full_msg)
                    return data # Success
                except pickle.UnpicklingError as e:
                    print(f"NETWORK RECV ERROR: Failed to unpickle data: {e}")
                    return None
                except Exception as e:
                    print(f"NETWORK RECV ERROR: Unexpected error during unpickle: {e}")
                    return None

            elif len(full_msg) > expected_msg_len:
                # This indicates a data stream corruption or logic error
                print(f"NETWORK RECV ERROR: Received more data than expected header size indicated. Header: {expected_msg_len}, Received: {len(full_msg)}")
                return None


        except socket.timeout:
            print("NETWORK RECV ERROR: Socket timeout.")
            return None # Indicate timeout
        except ConnectionResetError:
            print("NETWORK RECV ERROR: Connection reset by peer.")
            return None
        except socket.error as e:
            print(f"NETWORK RECV ERROR: Socket error: {e}")
            return None
        except Exception as e:
             print(f"NETWORK RECV ERROR: Unexpected error in receive_data: {e}")
             return None

def client_handler(conn, addr):
    """Handles communication with a single client in a separate thread."""
    global player_id_counter, combat_manager, npc_manager # Access shared data

    print(f"[SERVER] Connection established with {addr}")
    # 1. Assign a unique ID to the new player
    player_id = -1
    with threading.Lock(): # Protect access to shared player data
        player_id = player_id_counter
        player_id_counter += 1
        # Create a player object on the server for this client
        # Determine spawn point based on the current game state
        if game_state == "overworld":
             start_x = world_struct_stable.KINGDOM_CENTER_X + world_struct_stable.KINGDOM_RADIUS + 200 + (player_id * 50) # Simple offset spawn
             start_y = world_struct_stable.KINGDOM_CENTER_Y
        else: # Dungeon fallback
             start_x, start_y = 100 + (player_id * 50), 100
        # Ensure player assets are loaded before creating a Player instance
        if player_animations['idle'] and player_animations['dims']:
             new_player = player_module.Player(player_id, start_x, start_y, PLAYER_RADIUS, PLAYER_SPEED, PLAYER_COLOR, player_animations)
             network_players[player_id] = new_player # Add to the server's authoritative player list
             print(f"[SERVER] Assigned Player ID {player_id} to {addr}. Spawning at ({start_x},{start_y})")
        else:
             print(f"[SERVER] ERROR: Player assets not loaded when trying to create player {player_id}. Disconnecting.")
             conn.close()
             return # Exit thread


    # 2. Send the initial state to the new client
    initial_state = {
        'type': 'initial_state',
        'your_id': player_id,
        'players': {pid: p.get_network_state() for pid, p in network_players.items()},
        'enemies': combat_manager.get_all_enemies_network_state() if combat_manager else {},
    }
    if not send_data(conn, initial_state):
        print(f"[SERVER] Failed to send initial state to {addr}. Closing connection.")
        with threading.Lock():
             if player_id in network_players: del network_players[player_id]
        conn.close()
        return

    # 3. Main loop for receiving client input
    connected = True
    while connected:
        try:
            # Receive input data from the client
            data = receive_data(conn)

            if data is None: # Handle disconnection or receive error
                print(f"[SERVER] Receive error or connection closed for {addr} (Player {player_id}).")
                connected = False
                break

            if isinstance(data, dict) and 'type' in data:
                # Process messages based on their type
                if data['type'] == 'player_input':
                    # Update the server's representation of this player's input intention
                    player = network_players.get(player_id)
                    if player:
                        with threading.Lock(): # Protect player object access
                            # Apply received input to the player's request flags and vectors
                            player.last_known_move_vector = pygame.math.Vector2(data.get('move_vector', [0,0]))
                            player.attack_requested = data.get('attack', False)
                            player.interact_requested = data.get('interact', False)

        except Exception as e:
            print(f"[SERVER] Error in client handler for {addr} (Player {player_id}): {e}")
            connected = False # Assume disconnect on error

    # 4. Cleanup on disconnect
    print(f"[SERVER] Disconnecting {addr} (Player {player_id}).")
    with threading.Lock(): # Protect shared resources during removal
        if conn in clients:
            del clients[conn]
        if player_id in network_players:
            del network_players[player_id]
            # Broadcast a message to other clients that this player disconnected
            disconnect_msg = {'type': 'player_disconnect', 'id': player_id}
            broadcast_data(disconnect_msg, sender_socket=None)

    try:
        conn.close()
    except socket.error:
        pass # Ignore errors if socket is already closed

def start_server():
    """Initializes and starts the game server."""
    global server_socket, is_host, player_id_counter, my_player_id, network_players
    player_id_counter = 0 # Reset counter for a new server instance

    # Create the host's player object only if not a dedicated server
    if not is_dedicated_host:
        my_player_id = player_id_counter
        player_id_counter += 1
        # Determine spawn point for the host player
        if game_state == "overworld":
            start_x = world_struct_stable.KINGDOM_CENTER_X + world_struct_stable.KINGDOM_RADIUS + 200
            start_y = world_struct_stable.KINGDOM_CENTER_Y
        else: # Dungeon fallback
            start_x, start_y = 100, 100

        if player_animations['idle'] and player_animations['dims']:
            host_player = player_module.Player(my_player_id, start_x, start_y, PLAYER_RADIUS, PLAYER_SPEED, PLAYER_COLOR, player_animations)
            network_players[my_player_id] = host_player
            print(f"[SERVER] Host player created with Player ID {my_player_id} at ({start_x},{start_y}).")
        else:
            print("[SERVER] FATAL: Player assets not loaded. Cannot create host player.")
            if server_socket: server_socket.close()
            pygame.quit(); sys.exit()
    else:
        my_player_id = None # Dedicated host has no player representation
        print("[SERVER] Starting in dedicated mode. No host player created.")


    # Setup server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Allow reusing the address quickly
    try:
        server_socket.bind(('0.0.0.0', PORT)) # Bind to all available network interfaces
        server_socket.listen(MAX_CLIENTS)
        server_socket.setblocking(False) # Make server_socket.accept() non-blocking
        print(f"[SERVER] Listening on port {PORT}...")

    except socket.error as e:
        print(f"[SERVER] FATAL: Could not bind to port {PORT}: {e}")
        server_socket = None
        is_host = False # Cannot be a host if binding fails
        pygame.quit()
        sys.exit() # Exit if the server cannot start

def accept_connections():
    """Accepts new incoming connections without blocking."""
    global server_socket, clients, client_threads
    if not server_socket: return

    # Use select to check for readable sockets (new connections) without blocking
    readable, _, _ = select.select([server_socket], [], [], 0.01) # Small timeout

    if server_socket in readable:
        try:
            conn, addr = server_socket.accept()
            if len(clients) >= MAX_CLIENTS -1: # Check if server is full
                 print(f"[SERVER] Connection rejected from {addr}: Server full.")
                 send_data(conn, {'type':'error', 'message':'Server is full.'})
                 conn.close()
            else:
                 print(f"[SERVER] Accepted connection from {addr}")
                 clients[conn] = addr
                 # Start a new thread to handle this client's communication
                 thread = threading.Thread(target=client_handler, args=(conn, addr), daemon=True)
                 thread.start()
                 client_threads.append(thread)

        except socket.error as e:
            print(f"[SERVER] Error accepting connection: {e}")
        except Exception as e:
            print(f"[SERVER] Unexpected error during accept: {e}")

def connect_to_server(server_ip):
    """Connects the client to the specified server IP."""
    global client_socket, my_player_id, network_players, combat_manager, npc_manager
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((server_ip, PORT))
        print(f"[CLIENT] Connected to server {server_ip}:{PORT}")

        # 1. Receive initial state from the server
        initial_data = receive_data(client_socket)
        if initial_data and initial_data.get('type') == 'initial_state':
            my_player_id = initial_data.get('your_id')
            print(f"[CLIENT] Received Player ID: {my_player_id}")

            # Populate local network_players dictionary from server data
            server_players = initial_data.get('players', {})
            network_players = {} # Clear local dictionary first
            for p_id, p_state in server_players.items():
                # Create local Player objects based on the received state
                if player_animations['idle'] and player_animations['dims']:
                    player_obj = player_module.Player(p_id, p_state['x'], p_state['y'], PLAYER_RADIUS, PLAYER_SPEED, PLAYER_COLOR, player_animations)
                    player_obj.apply_network_state(p_state) # Apply the detailed state
                    network_players[p_id] = player_obj
                else:
                    print(f"[CLIENT] ERROR: Player assets not loaded when creating player {p_id}")

            # Update enemies based on the initial state
            server_enemies = initial_data.get('enemies', {})
            if combat_manager:
                 combat_manager.apply_enemy_network_state(server_enemies)

            # 2. Start a thread to continuously receive server updates
            receive_thread = threading.Thread(target=client_receive_loop, daemon=True)
            receive_thread.start()
            return True # Connection successful

        elif initial_data and initial_data.get('type') == 'error':
             print(f"[CLIENT] Server rejected connection: {initial_data.get('message', 'Unknown error')}")
             client_socket.close()
             client_socket = None
             return False

        else:
            print("[CLIENT] Failed to receive valid initial state from server.")
            client_socket.close()
            client_socket = None
            return False

    except socket.error as e:
        print(f"[CLIENT] Could not connect to server {server_ip}:{PORT} - {e}")
        client_socket = None
        return False
    except Exception as e:
        print(f"[CLIENT] Unexpected error during connection: {e}")
        client_socket = None
        return False

def client_receive_loop():
    """Listens for updates from the server in a separate thread."""
    global running, client_socket, network_players, combat_manager, npc_manager

    while running and client_socket:
        try:
            data = receive_data(client_socket)
            if data is None:
                print("[CLIENT] Disconnected from server (receive loop).")
                running = False # Stop the main game loop
                break

            # Process received data to update the local game state
            if isinstance(data, dict):
                msg_type = data.get('type')
                if msg_type == 'game_state_update':
                    # Update players
                    player_states = data.get('players', {})
                    with threading.Lock(): # Protect access to network_players
                        current_ids = set(network_players.keys())
                        received_ids = set(player_states.keys())

                        for p_id, p_state in player_states.items():
                            if p_id in network_players:
                                # Update existing player's state
                                network_players[p_id].apply_network_state(p_state)
                            else:
                                # A new player has joined; create them locally
                                if player_animations and player_animations['idle'] and player_animations['dims']:
                                    new_player = player_module.Player(p_id, p_state['x'], p_state['y'], PLAYER_RADIUS, PLAYER_SPEED, PLAYER_COLOR, player_animations)
                                    new_player.apply_network_state(p_state)
                                    network_players[p_id] = new_player
                                    print(f"[CLIENT] Player {p_id} joined.")
                                else:
                                    print(f"[CLIENT] ERROR: Assets not loaded, cannot create joined player {p_id}")

                        # Remove players who have disconnected
                        disconnected_ids = current_ids - received_ids
                        for p_id in disconnected_ids:
                            if p_id in network_players:
                                print(f"[CLIENT] Player {p_id} disconnected.")
                                del network_players[p_id]

                    # Update enemies with server's authoritative state
                    enemy_states = data.get('enemies', {})
                    if combat_manager:
                        combat_manager.apply_enemy_network_state(enemy_states)

                elif msg_type == 'player_disconnect':
                    # Handle explicit disconnect message from the server
                    p_id = data.get('id')
                    if p_id is not None:
                        with threading.Lock():
                             if p_id in network_players:
                                print(f"[CLIENT] Player {p_id} disconnected (message).")
                                del network_players[p_id]

        except Exception as e:
            print(f"[CLIENT] Error in receive loop: {e}")
            running = False # Stop the game on a major receive error
            break

    print("[CLIENT] Receive loop ended.")
    # Clean up the socket reference when the loop ends
    socket_ref = client_socket
    client_socket = None # Indicate socket is no longer valid
    if socket_ref:
        try:
            socket_ref.close()
        except:
            pass

def broadcast_data(data, sender_socket=None):
    """Sends data to all connected clients, optionally excluding the original sender."""
    if not is_host: return # Only the host can broadcast
    disconnected_clients = []
    with threading.Lock(): # Protect access to the clients dictionary
        # Create a copy of keys to iterate over, allowing modification of the original dict
        client_sockets = list(clients.keys())
        for client_conn in client_sockets:
            if client_conn != sender_socket:
                if not send_data(client_conn, data):
                    # Mark client for removal if sending data fails
                    disconnected_clients.append(client_conn)

    # Remove disconnected clients outside the iteration lock
    if disconnected_clients:
        with threading.Lock():
            for conn in disconnected_clients:
                if conn in clients:
                    print(f"[SERVER] Removing disconnected client {clients[conn]} due to send error.")
                    addr = clients.pop(conn) # Remove and get address
                    # Find corresponding player ID to remove from network_players
                    player_id_to_remove = None
                    # This requires a better mapping of connection to player ID for robust removal
                    if player_id_to_remove is not None and player_id_to_remove in network_players:
                         del network_players[player_id_to_remove]
                         print(f"[SERVER] Removed player object {player_id_to_remove}")

                    try:
                         conn.close()
                    except socket.error:
                         pass


# --- Initialization ---
pygame.init()
mixer_initialized = False
try:
    pygame.mixer.init()
    print("Pygame mixer initialized successfully.")
    mixer_initialized = True
except pygame.error as e:
    print(f"Error initializing pygame mixer: {e}. Music will not be available.")
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Explore the Realm! (Loading...)")
clock = pygame.time.Clock()

# --- Run Loading Screen ---
# This function loads all assets, generates the world, populates the quadtree,
# and initializes game managers.
(world_data, collision_quadtree,
effective_world_width, effective_world_height,
all_enemy_animations, player_animations,
combat_manager, npc_manager) = loading.run_loading_screen(screen, game_state, mixer_initialized)

# Check if loading was successful
if world_data is None or collision_quadtree is None or player_animations is None:
    print("FATAL ERROR: Loading failed. Exiting.")
    pygame.quit()
    sys.exit()

# --- Player Initialization ---
start_x, start_y = 100, 100 # Default starting position

if game_state == "dungeon":
    dungeon_rooms_grid = world_data.get("dungeon_rooms_grid")
    if dungeon_rooms_grid:
        # Start in a random room in the dungeon
        start_room_grid = random.choice(dungeon_rooms_grid)
        start_grid_x, start_grid_y = start_room_grid.center
        start_x = start_grid_x * world_struct_stable.DUNGEON_TILE_SIZE + world_struct_stable.DUNGEON_TILE_SIZE // 2
        start_y = start_grid_y * world_struct_stable.DUNGEON_TILE_SIZE + world_struct_stable.DUNGEON_TILE_SIZE // 2
        print(f"Player starting in dungeon at world ({start_x:.1f}, {start_y:.1f})")
    else:
        print("Error: No dungeon rooms found! Player at default (100,100).")

elif game_state == "overworld":
    # A starting point just outside the kingdom to the east
    start_x = world_struct_stable.KINGDOM_CENTER_X + world_struct_stable.KINGDOM_RADIUS + 200
    start_y = world_struct_stable.KINGDOM_CENTER_Y
    print(f"Player starting in overworld at ({start_x}, {start_y})")

# Now that loading is done, set the final window caption
pygame.display.set_caption(f"Explore the Realm! {'(Host)' if is_host else '(Client)'} ID: {my_player_id}")

# --- Game Loop Variables ---
running = True
last_time = pygame.time.get_ticks()
fight_check_timer = 0.0
FIGHT_COOLDOWN = 5.0 # Seconds before health regen restarts
last_input_state = {}

# --- Ask User: Host or Join ---
user_choice = ""
host_mode = None # Will be 'play' or 'dedicated' if hosting
while user_choice not in ['host', 'join']:
    user_choice = input("Do you want to (host) or (join) a game? ").lower().strip()

if user_choice == 'host':
    host_type_choice = ""
    while host_type_choice not in ['play', 'dedicated']:
        host_type_choice = input("Host type: (play) with others or run a (dedicated) server? ").lower().strip()

    if host_type_choice == 'play':
        is_host = True
        host_mode = 'play'
        is_dedicated_host = False
        print("[CONFIG] Starting as Host (Playing).")
        start_server() # Start the server process
        if not is_host: # Check if server start failed
            print("Failed to start server. Exiting.")
            pygame.quit(); sys.exit()
    elif host_type_choice == 'dedicated':
            is_host = True
            host_mode = 'dedicated'
            is_dedicated_host = True
            print("[CONFIG] Starting as Dedicated Host (Not Playing).")
            my_player_id = None # Dedicated host has no player ID
            start_server() # Start the server process
            if not is_host: # Check if server start failed
                print("Failed to start server. Exiting.")
                pygame.quit(); sys.exit()

            # --- Dedicated Host Loop (No Graphics) ---
            print("[DEDICATED SERVER] Running server loop...")
            last_time = pygame.time.get_ticks()
            while server_socket: # Loop as long as the server is running
                accept_connections()

                # Calculate delta time for consistent game speed
                current_time = pygame.time.get_ticks()
                if last_time > 0:
                    dt = min((current_time - last_time) / 1000.0, 0.1) # Capped to prevent large jumps
                else:
                    dt = 1.0 / FPS # Estimate for the first frame
                last_time = current_time

                # --- SERVER SIDE UPDATES ---
                if is_host:
                    # Update all players based on their last received input
                    player_ids = list(network_players.keys())
                    for p_id in player_ids:
                        player_obj = network_players.get(p_id)
                        if player_obj:
                            # Get nearby colliders for physics calculations
                            potential_colliders = []
                            if collision_quadtree and player_obj.rect:
                                query_range = player_obj.rect.inflate(player_obj.speed * 2 + 32, player_obj.speed * 2 + 32)
                                potential_colliders = collision_quadtree.query(query_range)

                            # Update player using their last known network input vector
                            player_obj.update(player_obj.last_known_move_vector, potential_colliders, dt, effective_world_width, effective_world_height)

                            # Process action requests received from clients
                            if player_obj.attack_requested:
                                if player_obj.start_attack_animation():
                                    combat_manager.handle_player_attack(player_obj)
                                player_obj.attack_requested = False # Consume the request

                            if player_obj.interact_requested:
                                npc_manager.handle_interaction(player_obj)
                                player_obj.interact_requested = False # Consume the request

                    # Update enemies and NPCs authoritatively on the server
                    if combat_manager: combat_manager.update(network_players, dt, collision_quadtree, game_state)
                    if npc_manager: npc_manager.update(dt, collision_quadtree)

                    # --- Prepare and Broadcast Game State ---
                    current_game_state_payload = {
                        'type': 'game_state_update',
                        'players': {pid: p.get_network_state() for pid, p in network_players.items() if p},
                        'enemies': combat_manager.get_all_enemies_network_state() if combat_manager else {},
                    }
                    broadcast_data(current_game_state_payload)

                clock.tick(FPS) # Maintain a consistent server tick rate

            # Exit if the server loop terminates
            print("[DEDICATED SERVER] Server loop finished. Exiting.")
            pygame.quit(); sys.exit()

else: # Join a game
    is_host = False
    is_dedicated_host = False
    server_ip_address = input("Enter the host's IP address: ")
    if not connect_to_server(server_ip_address):
        print("Failed to connect to server. Exiting.")
        pygame.quit(); sys.exit()

# Ensure the player object exists if in host-and-play mode
if host_mode == 'play' and my_player_id not in network_players:
    print("[ERROR] Host player object was not created correctly. Exiting.")
    pygame.quit(); sys.exit()


# --- Spawn dynamic entities (AUTHORITATIVE on SERVER) ---
if is_host:
    print("[SERVER] Spawning initial entities...")
    if combat_manager: # Ensure manager exists
        if game_state == "dungeon":
            combat_manager.spawn_enemies_in_dungeon(combat_mech_stable.SWORD_ORC_COUNT // 2)
            npc_manager.spawn_npcs_in_dungeon()
        elif game_state == "overworld":
            combat_manager.spawn_enemies_in_overworld(combat_mech_stable.SWORD_ORC_COUNT)
            npc_manager.spawn_npcs_in_overworld(world_struct_stable.KINGDOM_CENTER_X, world_struct_stable.KINGDOM_CENTER_Y, world_struct_stable.is_point_in_polygon)


# --- Play Background Music ---
if mixer_initialized:
    try:
        pygame.mixer.music.play(loops=-1) # Play indefinitely
        print("Music playing.")
    except pygame.error as e:
        print(f"Error playing music file '{assets.MUSIC_FILE_PATH}': {e}")


# --- Game Loop ---
while running:
    current_time = pygame.time.get_ticks()
    dt = min((current_time - last_time) / 1000.0, 0.1)
    last_time = current_time

    # --- Server: Accept new connections ---
    if is_host:
        accept_connections()

    # --- Get Local Player Reference (for drawing, camera, UI, input) ---
    local_player = None
    if not is_dedicated_host: # Only needed if this instance is a playable client
         with threading.Lock():
             local_player = network_players.get(my_player_id)

    # If the local player is gone (e.g., disconnected), stop the loop
    if not is_dedicated_host and local_player is None:
         print("Local player not found, stopping game loop.")
         running = False
         continue # Skip the rest of the loop

    # --- Event Handling ---
    interacted_this_frame = False
    attack_pressed_this_event = False
    local_player_moved = False

    if not is_dedicated_host and local_player: # Only handle events for a playable instance
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_m: show_map = not show_map
                if event.key == pygame.K_ESCAPE: running = False
                # Handle actions for the local player
                if not local_player.is_dead:
                    if event.key == pygame.K_e:
                        local_player.interact_requested = True # Flag the intent to interact
                    if event.key == pygame.K_SPACE:
                        local_player.attack_requested = True # Flag the intent to attack

    # --- Player Input (Get movement vector for local player) ---
    intended_move_vector = pygame.math.Vector2(0,0)
    if not is_dedicated_host and local_player:
        # Reads keyboard state and sets the player's movement vector
        local_player.handle_input()
        intended_move_vector = local_player.last_known_move_vector


    # --- Network Sending (Client sends input to Server) ---
    if not is_host and client_socket and local_player:
        current_input_state = {
            'type': 'player_input',
            'move_vector': [intended_move_vector.x, intended_move_vector.y],
            'attack': local_player.attack_requested,
            'interact': local_player.interact_requested,
        }
        # Send the current input state to the server
        if not send_data(client_socket, current_input_state):
             print("[CLIENT] Failed to send input data. Disconnecting.")
             running = False
        # Reset single-press flags after sending them
        local_player.attack_requested = False
        local_player.interact_requested = False

    # --- SERVER SIDE UPDATES ---
    if is_host:
        # --- Update Host Player (if not dedicated) ---
        if not is_dedicated_host and local_player:
            # Get nearby colliders for physics
            potential_colliders = []
            if collision_quadtree:
                query_range = local_player.rect.inflate(local_player.speed * 2 + 32, local_player.speed * 2 + 32)
                potential_colliders = collision_quadtree.query(query_range)

            # Update host player based on direct local input
            local_player.update(intended_move_vector, potential_colliders, dt, effective_world_width, effective_world_height)

            # Process the host's own action requests
            if local_player.attack_requested:
                if local_player.start_attack_animation():
                    combat_manager.handle_player_attack(local_player)
                local_player.attack_requested = False

            if local_player.interact_requested:
                npc_manager.handle_interaction(local_player)
                local_player.interact_requested = False

        # --- Update Client Players (Based on received input) ---
        player_ids = list(network_players.keys())
        for p_id in player_ids:
            # Skip host player (already updated)
            if p_id == my_player_id or p_id not in network_players:
                continue

            player_obj = network_players[p_id]
            if player_obj:
                # Get nearby colliders
                potential_colliders = []
                if collision_quadtree:
                    query_range = player_obj.rect.inflate(player_obj.speed * 2 + 32, player_obj.speed * 2 + 32)
                    potential_colliders = collision_quadtree.query(query_range)

                # Update client's player based on their last received move vector
                player_obj.update(player_obj.last_known_move_vector, potential_colliders, dt, effective_world_width, effective_world_height)

                # Process client's action requests
                if player_obj.attack_requested:
                    if player_obj.start_attack_animation():
                        combat_manager.handle_player_attack(player_obj)
                    player_obj.attack_requested = False # Reset flag on server

                if player_obj.interact_requested:
                    npc_manager.handle_interaction(player_obj)
                    player_obj.interact_requested = False # Reset flag on server


        # --- Update Enemies & NPCs (Server Authority) ---
        if combat_manager:
            combat_manager.update(network_players, dt, collision_quadtree, game_state)
        if npc_manager:
            npc_manager.update(dt, collision_quadtree)


        # --- Prepare and Broadcast Game State ---
        current_game_state_payload = {
            'type': 'game_state_update',
            'players': {pid: p.get_network_state() for pid, p in network_players.items() if p},
            'enemies': combat_manager.get_all_enemies_network_state() if combat_manager else {},
        }
        broadcast_data(current_game_state_payload)


    # --- Camera Update (Based on LOCAL player) ---
    if not is_dedicated_host and local_player:
        camera_map.update_camera(local_player.x, local_player.y, effective_world_width, effective_world_height)
        camera_x = camera_map.camera_x
        camera_y = camera_map.camera_y
    else:
        # No camera needed for dedicated host
        camera_x, camera_y = 0, 0


    # --- Drawing (Client and Host-Play draw the world based on received network state) ---
    if not is_dedicated_host:
        screen.fill(world_struct_stable.GRASS_COLOR_BASE)

        # Draw static world elements
        drawing.draw_world_background(screen, camera_x, camera_y, world_data, game_state)
        drawing.draw_world_details(screen, camera_x, camera_y, world_data, game_state)

        if game_state == "overworld":
            drawing.draw_kingdom_structures(screen, camera_x, camera_y, world_data)

        # --- Draw Dynamic Entities ---
        draw_list = []
        with threading.Lock(): # Protect access while iterating network dictionaries
            # Add players to the draw list
            for p_id, p_obj in network_players.items():
                if p_obj: draw_list.append({'type': 'player', 'object': p_obj, 'y': p_obj.y})
            # Add enemies to the draw list
            enemies_to_draw = combat_manager.client_enemies if not is_host else combat_manager.enemies
            for enemy in list(enemies_to_draw.values()) if isinstance(enemies_to_draw, dict) else enemies_to_draw:
                if enemy: draw_list.append({'type': 'enemy', 'object': enemy, 'y': enemy.y})

        # Sort by Y-coordinate for proper depth perception (sprite layering)
        draw_list.sort(key=lambda item: item['y'])

        # Draw sorted entities
        for item in draw_list:
            obj = item['object']
            cam_func = camera_map.apply_camera_to_point
            if item['type'] == 'player':
                is_local = (obj.player_id == my_player_id)
                obj.draw(screen, cam_func, is_local)
            elif item['type'] == 'enemy':
                obj.draw(screen, cam_func)
            elif item['type'] == 'npc':
                 pass # NPC drawing is handled by the manager

        # Draw map overlay if toggled
        if show_map and local_player:
            camera_map.draw_map_overlay(screen, local_player, world_data, effective_world_width, effective_world_height, game_state, list(network_players.values()))


        # Draw UI Elements
        if local_player:
            ui.draw_ui(screen, local_player)
        if npc_manager:
            npc_manager.draw_dialogue(screen)

        # Update the full display Surface to the screen
        pygame.display.flip()


    # Control Framerate
    clock.tick(FPS)


# --- Quit ---
print("Game loop ended. Cleaning up...")
running = False # Signal threads to stop

# Close network connections
if is_host and server_socket:
    print("[SERVER] Closing server socket.")
    server_socket.close()
if not is_host and client_socket:
    print("[CLIENT] Closing client socket.")
    client_socket.close()


# Clean up Pygame modules
pygame.mixer.music.stop()
pygame.mixer.quit()
pygame.font.quit()
pygame.quit()
print("Exiting.")
sys.exit()

