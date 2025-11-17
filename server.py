import socket
import threading
import json
import time
from common import PlayerBoard, SHIP_SIZES  # Import from our common file

HOST = '0.0.0.0'  # Listen on all network interfaces
PORT = 65432
MAX_PLAYERS = 2

clients = []  # List to hold client socket objects
player_boards = {}  # Dictionary to map client_socket -> PlayerBoard
player_names = {}
client_placement_done = {}
game_state = "Waiting"  # Waiting, Placement, Attack
turn_index = 0


def send_to_all(message):
    """Sends a message to all connected clients."""
    for client in clients:
        send_to_client(client, message)


def send_to_client(client, message):
    """Sends a message to a single client."""
    try:
        data = json.dumps(message).encode('utf-8')
        # Prepend with 8-byte length header
        header = f"{len(data):<8}".encode('utf-8')
        client.sendall(header + data)
    except Exception as e:
        print(f"[SERVER] Error sending message: {e}")


def handle_client(client_socket, player_name):
    """Handles messages from a single client in a thread."""
    global game_state, turn_index

    player_boards[client_socket] = PlayerBoard(player_name)
    player_names[client_socket] = player_name
    client_placement_done[client_socket] = False

    # Tell the client their name
    send_to_client(client_socket, {"type": "GREETING", "name": player_name})

    if len(clients) == MAX_PLAYERS:
        game_state = "Placement"
        print("[SERVER] Both players connected. Starting placement phase.")
        send_to_all({"type": "START_PLACEMENT", "message": "Both players connected. Place your ships!"})

    while True:
        try:
            # Read header
            header = client_socket.recv(8)
            if not header:
                break
            msg_len = int(header.decode('utf-8').strip())

            # Read full message
            data = b''
            while len(data) < msg_len:
                packet = client_socket.recv(msg_len - len(data))
                if not packet:
                    break
                data += packet

            message = json.loads(data.decode('utf-8'))
            msg_type = message.get('type')

            if msg_type == 'PLACEMENT_DONE':
                # Client sent their board
                player_boards[client_socket].ships = message['ships']
                player_boards[client_socket].grid = message['grid']
                client_placement_done[client_socket] = True
                print(f"[SERVER] {player_name} has finished placement.")

                # Check if all players are done
                if all(client_placement_done.values()):
                    game_state = "Attack"
                    turn_index = 0  # Player 1 (first to connect) goes first
                    attacker = clients[turn_index]
                    defender = clients[1 - turn_index]

                    print("[SERVER] All players ready. Starting attack phase.")
                    send_to_client(attacker,
                                   {"type": "START_ATTACK", "turn": True, "message": "Your turn! Fire a shot."})
                    send_to_client(defender, {"type": "START_ATTACK", "turn": False, "message": "Opponent's turn."})

            elif msg_type == 'SHOT':
                if game_state != "Attack" or client_socket != clients[turn_index]:
                    send_to_client(client_socket,
                                   {"type": "ERROR", "message": "Not your turn or game not in Attack phase."})
                    continue

                col, row = message['col'], message['row']
                attacker = clients[turn_index]
                defender = clients[1 - turn_index]
                defender_board = player_boards[defender]

                result, is_sunk = defender_board.receive_shot(col, row)
                print(f"[SERVER] {player_name} fired at ({col},{row}). Result: {result}")

                # Send result to attacker
                send_to_client(attacker, {"type": "SHOT_RESULT", "col": col, "row": row, "result": result,
                                          "sunk_count": defender_board.ships_sunk_count})
                # Send notice to defender
                send_to_client(defender, {"type": "OPPONENT_SHOT", "col": col, "row": row, "result": result,
                                          "sunk_count": defender_board.ships_sunk_count})

                # Check for win
                if defender_board.ships_sunk_count == len(SHIP_SIZES):
                    print(f"[SERVER] Game Over! {player_names[attacker]} wins!")
                    send_to_all({"type": "GAME_OVER", "winner": player_names[attacker]})
                    game_state = "Waiting"  # Reset for new game?
                    break

                # If it was a miss, switch turns
                if result == 'Miss':
                    turn_index = 1 - turn_index  # Flip 0 to 1 or 1 to 0
                    send_to_client(clients[turn_index], {"type": "YOUR_TURN"})
                    send_to_client(clients[1 - turn_index], {"type": "OPPONENT_TURN"})
                    print(f"[SERVER] Turn switched. It is now {player_names[clients[turn_index]]}'s turn.")

        except Exception as e:
            print(f"[SERVER] Error handling client {player_name}: {e}")
            break

    # Cleanup on disconnect
    print(f"[SERVER] {player_name} disconnected.")
    clients.remove(client_socket)
    del player_boards[client_socket]
    del player_names[client_socket]
    del client_placement_done[client_socket]
    client_socket.close()


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(MAX_PLAYERS)

    try:
        my_ip = socket.gethostbyname(socket.gethostname())
        print(f"*** Battleship Server Started ***")
        print(f"Share this IP with your opponent: {my_ip}")
        print(f"Listening on port {PORT}...")
    except:
        print(f"*** Battleship Server Started ***")
        print(f"Listening on {HOST}:{PORT}... (Could not determine local IP)")

    while True:
        if len(clients) < MAX_PLAYERS:
            client_socket, addr = server_socket.accept()
            clients.append(client_socket)
            player_name = f"Player {len(clients)}"
            print(f"[SERVER] {player_name} connected from {addr}")

            thread = threading.Thread(target=handle_client, args=(client_socket, player_name))
            thread.daemon = True
            thread.start()
        else:
            # Simple way to prevent more connections
            time.sleep(1)


if __name__ == "__main__":
    main()