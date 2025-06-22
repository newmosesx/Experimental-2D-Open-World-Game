# --- Network Constants ---
PORT = 5555 # Port for the server to listen on
HEADER_SIZE = 10 # Fixed size for message length header
MAX_CLIENTS = 3 # Maximum number of clients the server will accept (including host)

# Network Variables
is_host = False
is_dedicated_host = False # self explanatory dedicated and host (playing) flags
client_socket = None # Socket for clients connecting to the server
server_socket = None # Socket for the server listening for clients
clients = {} # Server: Dictionary to store connected client sockets and addresses {client_socket: address}
client_threads = [] # Server: List to hold client handling threads
player_id_counter = 0 # Server: Simple way to assign unique IDs
network_players = {} # All instances: Dictionary to store player data {player_id: player_object_or_data}
my_player_id = None # Client/Host: This instance's unique ID

