import tkinter as tk
from tkinter import messagebox, simpledialog
import math
import socket
import threading
import json
import sys
import random
import time

# Import all our common classes and functions
from common import (
    PlayerBoard, GRID_SIZE, SQUARE_SIZE, CANVAS_SIZE, SHIP_SIZES, SHIP_COLORS,
    draw_grid_lines, draw_hit_marker, draw_miss_marker
)


# ---
# ---
# --- GAME MODE 1: PLAYER VS. BOT (PvE) ---
# ---
# ---

class BattleshipGame_PvE(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Battleship - Player vs. Bot")
        self.geometry(f"{CANVAS_SIZE * 2 + 150}x{CANVAS_SIZE + 200}")

        # Game State
        self.player_board = PlayerBoard("Player 1")
        self.bot_board = PlayerBoard("Bot")

        self.current_ship_orientation = 'H'
        self.game_phase = 'Placement'  # Placement, Attack
        self.player_turn = True

        # GUI Elements
        self.frame = tk.Frame(self)
        self.frame.pack(pady=10)

        self.status_var = tk.StringVar(self, "Welcome! Place your ships on the LEFT board.")
        self.status_label = tk.Label(self, textvariable=self.status_var, font=('Arial', 14, 'bold'))
        self.status_label.pack(side=tk.TOP, pady=10)

        self.rotate_button = tk.Button(self, text="Rotate (R)", command=self.rotate_ship, font=('Arial', 12))
        self.rotate_button.pack(side=tk.BOTTOM, pady=5)

        self.setup_canvas()
        self.bind('<r>', lambda event: self.rotate_ship())

        self.draw_placement_board()

    def setup_canvas(self):
        self.ship_canvas = tk.Canvas(self.frame, width=CANVAS_SIZE, height=CANVAS_SIZE, bg='lightblue',
                                     highlightthickness=1)
        self.ship_canvas.pack(side=tk.LEFT, padx=10)
        self.ship_canvas.bind('<Button-1>', self.canvas_click)
        self.ship_canvas.bind('<Motion>', self.canvas_move)

        self.opponent_canvas = tk.Canvas(self.frame, width=CANVAS_SIZE, height=CANVAS_SIZE, bg='lightgray',
                                         highlightthickness=1)
        self.opponent_canvas.pack(side=tk.RIGHT, padx=10)

    def draw_grid(self, canvas, draw_ships=True, board=None):
        canvas.delete("all")
        draw_grid_lines(canvas)

        if board is None:
            board = self.player_board

        if draw_ships:
            self.draw_ships_on_canvas(canvas, board)
        else:
            self.draw_shots_on_canvas(canvas, board)

    def draw_ships_on_canvas(self, canvas, player):
        for ship in player.ships:
            c, r = ship['col'], ship['row']
            size, orientation = ship['size'], ship['orientation']

            x1, y1 = c * SQUARE_SIZE, r * SQUARE_SIZE
            width = SQUARE_SIZE * size if orientation == 'H' else SQUARE_SIZE
            height = SQUARE_SIZE if orientation == 'H' else SQUARE_SIZE * size
            x2, y2 = x1 + width, y1 + height

            color = SHIP_COLORS.get(size, "gray")
            canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black")

            if self.game_phase == 'Attack':
                for i in range(size):
                    hit_col = c + i if orientation == 'H' else c
                    hit_row = r + i if orientation == 'V' else r
                    if player.grid[hit_row][hit_col] == 'H':
                        draw_hit_marker(canvas, hit_col, hit_row)

    def draw_shots_on_canvas(self, canvas, player):
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                shot = player.shots_fired[r][c]
                if shot == 'H':
                    draw_hit_marker(canvas, c, r)
                elif shot == 'M':
                    draw_miss_marker(canvas, c, r)

    def rotate_ship(self):
        if self.game_phase == 'Placement' and self.player_board.current_ship_index < len(SHIP_SIZES):
            self.current_ship_orientation = 'V' if self.current_ship_orientation == 'H' else 'H'
            self.update_status()
            if hasattr(self, '_last_mouse_coords'):
                self.canvas_move(self._last_mouse_coords)

    def draw_placement_board(self):
        self.status_label.config(fg='black')
        self.ship_canvas.config(bg='lightblue')
        self.opponent_canvas.config(bg='lightgray')
        self.opponent_canvas.delete("all")
        draw_grid_lines(self.opponent_canvas)
        self.draw_grid(self.ship_canvas, draw_ships=True, board=self.player_board)
        self.update_status()

    def start_attack_phase(self):
        self.game_phase = 'Attack'
        self.status_label.config(fg='black')
        self.ship_canvas.config(bg='lightblue')
        self.opponent_canvas.config(bg='lightcoral')
        self.opponent_canvas.bind('<Button-1>', self.canvas_click)

        self.draw_grid(self.ship_canvas, draw_ships=True, board=self.player_board)
        self.draw_grid(self.opponent_canvas, draw_ships=False, board=self.player_board)

        self.update_status()
        self.rotate_button.config(state=tk.DISABLED)

    def bot_place_ships(self):
        for size in SHIP_SIZES:
            placed = False
            while not placed:
                col = random.randint(0, GRID_SIZE - 1)
                row = random.randint(0, GRID_SIZE - 1)
                orientation = random.choice(['H', 'V'])

                if self.bot_board.is_valid_placement(size, col, row, orientation):
                    self.bot_board.add_ship(size, col, row, orientation)
                    placed = True

        self.start_attack_phase()

    def bot_take_turn(self):
        chosen = False
        while not chosen:
            col = random.randint(0, GRID_SIZE - 1)
            row = random.randint(0, GRID_SIZE - 1)

            if self.bot_board.shots_fired[row][col] == 0:
                chosen = True

        result, is_sunk = self.player_board.receive_shot(col, row)
        shot_mark = 'H' if result in ('Hit', 'Sunk') else 'M'
        self.bot_board.shots_fired[row][col] = shot_mark

        self.draw_grid(self.ship_canvas, draw_ships=True, board=self.player_board)

        coord_str = f"{chr(ord('A') + col)}{row + 1}"

        if self.player_board.ships_sunk_count == len(SHIP_SIZES):
            self.status_var.set(f"Bot {result} at {coord_str}!")
            messagebox.showinfo("Game Over!", "The Bot Wins!")
            self.destroy()
            return

        if result == 'Sunk':
            self.status_var.set(f"Bot SANK your ship at {coord_str}! Bot attacks again.")
            self.after(1000, self.bot_take_turn)
        elif result == 'Hit':
            self.status_var.set(f"Bot HIT at {coord_str}! Bot attacks again.")
            self.after(1000, self.bot_take_turn)
        else:  # Miss
            self.status_var.set(f"Bot MISSED at {coord_str}. Your turn!")
            self.player_turn = True
            self.opponent_canvas.bind('<Button-1>', self.canvas_click)

    def canvas_move(self, event):
        if self.game_phase != 'Placement':
            return

        self._last_mouse_coords = event

        c, r = self.get_grid_coords(event.x, event.y)
        if self.player_board.current_ship_index >= len(SHIP_SIZES):
            self.ship_canvas.delete("ghost")
            return

        current_size = SHIP_SIZES[self.player_board.current_ship_index]
        is_valid = self.player_board.is_valid_placement(current_size, c, r, self.current_ship_orientation)

        self.ship_canvas.delete("ghost")
        # Redraw ships *first* to clear old ghost
        self.draw_grid(self.ship_canvas, draw_ships=True, board=self.player_board)

        x1, y1 = c * SQUARE_SIZE, r * SQUARE_SIZE
        width = SQUARE_SIZE * current_size if self.current_ship_orientation == 'H' else SQUARE_SIZE
        height = SQUARE_SIZE if self.current_ship_orientation == 'H' else SQUARE_SIZE * current_size
        x2, y2 = x1 + width, y1 + height

        color = 'green' if is_valid else 'red'
        self.ship_canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=3, tags="ghost")

    def canvas_click(self, event):
        c, r = self.get_grid_coords(event.x, event.y)

        if not (0 <= c < GRID_SIZE and 0 <= r < GRID_SIZE):
            return

        if self.game_phase == 'Placement' and event.widget == self.ship_canvas:
            self.handle_placement_click(c, r)
        elif self.game_phase == 'Attack' and self.player_turn and event.widget == self.opponent_canvas:
            self.handle_attack_click(c, r)

    def handle_placement_click(self, c, r):
        if self.player_board.current_ship_index >= len(SHIP_SIZES):
            return

        current_size = SHIP_SIZES[self.player_board.current_ship_index]

        if self.player_board.is_valid_placement(current_size, c, r, self.current_ship_orientation):
            self.player_board.add_ship(current_size, c, r, self.current_ship_orientation)
            self.ship_canvas.delete("ghost")
            self.draw_grid(self.ship_canvas, draw_ships=True, board=self.player_board)
            self.update_status()

            if self.player_board.ships_placed_count == len(SHIP_SIZES):
                self.status_var.set("Player placement complete. Bot is placing ships...")
                self.ship_canvas.unbind('<Motion>')
                self.ship_canvas.unbind('<Button-1>')
                self.after(500, self.bot_place_ships)
        else:
            self.status_var.set("Invalid Placement! Try again.")
            self.status_label.config(fg='red')

    def handle_attack_click(self, c, r):
        if self.player_board.shots_fired[r][c] != 0:
            self.status_var.set("You already fired here! Choose a new target.")
            self.status_label.config(fg='red')
            return

        result, is_sunk = self.bot_board.receive_shot(c, r)
        shot_mark = 'H' if result in ('Hit', 'Sunk') else 'M'
        self.player_board.shots_fired[r][c] = shot_mark

        self.draw_grid(self.opponent_canvas, draw_ships=False, board=self.player_board)

        if self.bot_board.ships_sunk_count == len(SHIP_SIZES):
            self.status_var.set(f"You {result} at {chr(ord('A') + c)}{r + 1}!")
            messagebox.showinfo("Game Over!", "You Win!")
            self.destroy()
            return

        if result == 'Sunk':
            self.status_var.set(f"HIT! You SANK the bot's ship! Attack again.")
            self.status_label.config(fg='green')
        elif result == 'Hit':
            self.status_var.set(f"HIT! Attack again.")
            self.status_label.config(fg='green')
        else:  # Miss
            self.status_var.set(f"MISS! Bot's turn...")
            self.status_label.config(fg='blue')
            self.player_turn = False
            self.opponent_canvas.unbind('<Button-1>')

            self.after(1000, self.bot_take_turn)

    def get_grid_coords(self, x, y):
        col = x // SQUARE_SIZE
        row = y // SQUARE_SIZE
        return col, row

    def update_status(self):
        self.status_label.config(fg='black')
        if self.game_phase == 'Placement':
            if self.player_board.current_ship_index < len(SHIP_SIZES):
                size = SHIP_SIZES[self.player_board.current_ship_index]
                orientation = "Horizontal" if self.current_ship_orientation == 'H' else "Vertical"
                msg = f"Place Ship of size {size} | Orientation: {orientation} ('R' to rotate)"
            else:
                msg = "All ships placed! Bot is preparing..."
            self.status_var.set(msg)
        elif self.game_phase == 'Attack':
            if self.player_turn:
                self.status_var.set("Your Turn: Fire a shot on the RED board.")
            else:
                self.status_var.set("Bot's Turn...")


# ---
# ---
# --- GAME MODE 2: NETWORK CLIENT (PvP) ---
# ---
# ---

class BattleshipGame_Client(tk.Tk):
    def __init__(self, host_ip):
        super().__init__()
        self.title("Battleship - Network Client")
        self.geometry(f"{CANVAS_SIZE * 2 + 150}x{CANVAS_SIZE + 200}")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.host_ip = host_ip
        self.sock = None
        self.network_thread = None
        self.player_name = "Player"

        # Game State
        self.my_board = PlayerBoard("MyBoard")
        self.current_ship_orientation = 'H'
        self.game_phase = 'Setup'  # Setup, Placement, Attack, Waiting
        self.my_turn = False

        # GUI Elements
        self.frame = tk.Frame(self)
        self.frame.pack(pady=10)

        self.status_var = tk.StringVar(self, f"Connecting to {self.host_ip}...")
        self.status_label = tk.Label(self, textvariable=self.status_var, font=('Arial', 14, 'bold'))
        self.status_label.pack(side=tk.TOP, pady=10)

        self.rotate_button = tk.Button(self, text="Rotate (R)", command=self.rotate_ship, font=('Arial', 12),
                                       state=tk.DISABLED)
        self.rotate_button.pack(side=tk.BOTTOM, pady=5)

        self.setup_canvas()
        self.bind('<r>', lambda event: self.rotate_ship())

        # Start connection
        self.connect_to_server()

    def setup_canvas(self):
        self.ship_canvas = tk.Canvas(self.frame, width=CANVAS_SIZE, height=CANVAS_SIZE, bg='lightgray',
                                     highlightthickness=1)
        self.ship_canvas.pack(side=tk.LEFT, padx=10)

        self.opponent_canvas = tk.Canvas(self.frame, width=CANVAS_SIZE, height=CANVAS_SIZE, bg='lightgray',
                                         highlightthickness=1)
        self.opponent_canvas.pack(side=tk.RIGHT, padx=10)

    # --- Drawing Functions ---

    def draw_my_board(self):
        """Draws the player's own board (left canvas)."""
        canvas = self.ship_canvas
        canvas.delete("all")
        draw_grid_lines(canvas)

        # Draw ships
        for ship in self.my_board.ships:
            c, r = ship['col'], ship['row']
            size, orientation = ship['size'], ship['orientation']

            x1, y1 = c * SQUARE_SIZE, r * SQUARE_SIZE
            width = SQUARE_SIZE * size if orientation == 'H' else SQUARE_SIZE
            height = SQUARE_SIZE if orientation == 'H' else SQUARE_SIZE * size
            x2, y2 = x1 + width, y1 + height

            color = SHIP_COLORS.get(size, "gray")
            canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black")

        # Draw hits/misses on my board
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self.my_board.grid[r][c] == 'H':
                    draw_hit_marker(canvas, c, r)
                elif self.my_board.grid[r][c] == 'M':
                    draw_miss_marker(canvas, c, r)

    def draw_opponent_board(self):
        """Draws the opponent's board (right canvas) showing player's shots."""
        canvas = self.opponent_canvas
        canvas.delete("all")
        draw_grid_lines(canvas)

        # Draw shots fired
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                shot = self.my_board.shots_fired[r][c]
                if shot == 'H':
                    draw_hit_marker(canvas, c, r)
                elif shot == 'M':
                    draw_miss_marker(canvas, c, r)

    def rotate_ship(self):
        if self.game_phase == 'Placement' and self.my_board.current_ship_index < len(SHIP_SIZES):
            self.current_ship_orientation = 'V' if self.current_ship_orientation == 'H' else 'H'
            self.update_status()
            if hasattr(self, '_last_mouse_coords'):
                self.canvas_move(self._last_mouse_coords)

    # --- Network Functions ---

    def connect_to_server(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host_ip, 65432))

            self.network_thread = threading.Thread(target=self.listen_to_server)
            self.network_thread.daemon = True
            self.network_thread.start()
            self.status_var.set("Connected! Waiting for opponent...")
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect to {self.host_ip}: {e}")
            self.destroy()

    def listen_to_server(self):
        """Runs in a separate thread to receive messages from the server."""
        while True:
            try:
                # Read header
                header = self.sock.recv(8)
                if not header:
                    break
                msg_len = int(header.decode('utf-8').strip())

                # Read full message
                data = b''
                while len(data) < msg_len:
                    packet = self.sock.recv(msg_len - len(data))
                    if not packet:
                        break
                    data += packet

                message = json.loads(data.decode('utf-8'))

                # Safely update GUI from the main thread
                self.after(0, self.handle_server_message, message)

            except Exception as e:
                print(f"Error in listen_to_server: {e}")
                self.after(0, lambda: self.status_var.set("Connection to server lost."))
                break

    def send_to_server(self, message):
        """Sends a message to the server."""
        try:
            data = json.dumps(message).encode('utf-8')
            header = f"{len(data):<8}".encode('utf-8')
            self.sock.sendall(header + data)
        except Exception as e:
            self.status_var.set(f"Error sending message: {e}")

    def handle_server_message(self, message):
        """Processes messages from the server on the main GUI thread."""
        msg_type = message.get("type")

        if msg_type == "GREETING":
            self.player_name = message['name']
            self.title(f"Battleship - {self.player_name}")

        elif msg_type == "START_PLACEMENT":
            self.game_phase = "Placement"
            self.ship_canvas.config(bg='lightblue')
            self.opponent_canvas.config(bg='lightgray')
            self.draw_my_board()
            self.draw_opponent_board()
            self.rotate_button.config(state=tk.NORMAL)
            self.ship_canvas.bind('<Button-1>', self.canvas_click)
            self.ship_canvas.bind('<Motion>', self.canvas_move)
            self.update_status()

        elif msg_type == "START_ATTACK":
            self.game_phase = "Attack"
            self.my_turn = message['turn']
            self.ship_canvas.config(bg='lightblue')
            self.opponent_canvas.config(bg='lightcoral')
            self.draw_my_board()
            self.draw_opponent_board()
            self.rotate_button.config(state=tk.DISABLED)
            self.ship_canvas.unbind('<Button-1>')
            self.ship_canvas.unbind('<Motion>')
            if self.my_turn:
                self.opponent_canvas.bind('<Button-1>', self.canvas_click)
            self.update_status()

        elif msg_type == "YOUR_TURN":
            self.my_turn = True
            self.opponent_canvas.bind('<Button-1>', self.canvas_click)
            self.update_status()

        elif msg_type == "OPPONENT_TURN":
            self.my_turn = False
            self.opponent_canvas.unbind('<Button-1>')
            self.update_status()

        elif msg_type == "SHOT_RESULT":
            # This is the result of *my* shot
            c, r = message['col'], message['row']
            result = message['result']
            shot_mark = 'H' if result in ('Hit', 'Sunk') else 'M'

            self.my_board.shots_fired[r][c] = shot_mark
            self.draw_opponent_board()  # Redraw to show the new shot

            if result == 'Sunk':
                self.status_var.set(f"You SANK their ship! Attack again.")
                self.my_turn = True
                self.opponent_canvas.bind('<Button-1>', self.canvas_click)
            elif result == 'Hit':
                self.status_var.set(f"HIT! Attack again.")
                self.my_turn = True
                self.opponent_canvas.bind('<Button-1>', self.canvas_click)
            else:  # Miss
                self.status_var.set("MISS. Opponent's turn.")
                self.my_turn = False

        elif msg_type == "OPPONENT_SHOT":
            # This is the result of *their* shot on *my* board
            c, r = message['col'], message['row']
            result = message['result']

            # The server already updated its board, we just need to mirror it
            self.my_board.grid[r][c] = 'H' if result in ('Hit', 'Sunk') else 'M'
            self.draw_my_board()  # Redraw to show the new damage
            self.update_status()  # Update status to "Your Turn"

        elif msg_type == "GAME_OVER":
            self.game_phase = "Waiting"
            self.opponent_canvas.unbind('<Button-1>')
            winner = message['winner']
            if winner == self.player_name:
                messagebox.showinfo("Game Over", "You Win!")
            else:
                messagebox.showinfo("Game Over", f"{winner} Wins!")
            self.destroy()

    # --- Event Handlers ---

    def canvas_move(self, event):
        if self.game_phase != 'Placement':
            return

        self._last_mouse_coords = event
        c, r = self.get_grid_coords(event.x, event.y)

        if self.my_board.current_ship_index >= len(SHIP_SIZES):
            self.ship_canvas.delete("ghost")
            return

        current_size = SHIP_SIZES[self.my_board.current_ship_index]
        is_valid = self.my_board.is_valid_placement(current_size, c, r, self.current_ship_orientation)

        self.ship_canvas.delete("ghost")
        # Redraw ships *first* to clear old ghost
        self.draw_my_board()

        x1, y1 = c * SQUARE_SIZE, r * SQUARE_SIZE
        width = SQUARE_SIZE * current_size if self.current_ship_orientation == 'H' else SQUARE_SIZE
        height = SQUARE_SIZE if self.current_ship_orientation == 'H' else SQUARE_SIZE * current_size
        x2, y2 = x1 + width, y1 + height

        color = 'green' if is_valid else 'red'
        self.ship_canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=3, tags="ghost")

    def canvas_click(self, event):
        c, r = self.get_grid_coords(event.x, event.y)

        if not (0 <= c < GRID_SIZE and 0 <= r < GRID_SIZE):
            return

        if self.game_phase == 'Placement' and event.widget == self.ship_canvas:
            self.handle_placement_click(c, r)
        elif self.game_phase == 'Attack' and self.my_turn and event.widget == self.opponent_canvas:
            self.handle_attack_click(c, r)

    def handle_placement_click(self, c, r):
        if self.my_board.current_ship_index >= len(SHIP_SIZES):
            return

        current_size = SHIP_SIZES[self.my_board.current_ship_index]

        if self.my_board.is_valid_placement(current_size, c, r, self.current_ship_orientation):
            self.my_board.add_ship(current_size, c, r, self.current_ship_orientation)
            self.draw_my_board()
            self.update_status()

            if self.my_board.ships_placed_count == len(SHIP_SIZES):
                self.status_var.set("Placement complete. Waiting for opponent...")
                self.game_phase = "Waiting"
                self.rotate_button.config(state=tk.DISABLED)
                self.ship_canvas.unbind('<Motion>')
                self.ship_canvas.unbind('<Button-1>')

                # Send final board to server
                self.send_to_server({
                    "type": "PLACEMENT_DONE",
                    "ships": self.my_board.ships,
                    "grid": self.my_board.grid
                })
        else:
            self.status_var.set("Invalid Placement! Try again.")
            self.status_label.config(fg='red')

    def handle_attack_click(self, c, r):
        if self.my_board.shots_fired[r][c] != 0:
            self.status_var.set("You already fired here! Choose a new target.")
            self.status_label.config(fg='red')
            return

        # Send shot to server. Don't update GUI yet.
        # GUI will update when "SHOT_RESULT" is received.
        self.my_turn = False  # Prevent firing multiple times
        self.opponent_canvas.unbind('<Button-1>')
        self.status_var.set(f"Firing at {chr(ord('A') + c)}{r + 1}...")
        self.send_to_server({"type": "SHOT", "col": c, "row": r})

    # --- Utility Methods ---

    def get_grid_coords(self, x, y):
        col = x // SQUARE_SIZE
        row = y // SQUARE_SIZE
        return col, row

    def update_status(self):
        self.status_label.config(fg='black')
        if self.game_phase == 'Placement':
            if self.my_board.current_ship_index < len(SHIP_SIZES):
                size = SHIP_SIZES[self.my_board.current_ship_index]  # Corrected typo from 'my_band'
                orientation = "Horizontal" if self.current_ship_orientation == 'H' else "Vertical"
                msg = f"Place Ship of size {size} | Orientation: {orientation} ('R' to rotate)"
            else:
                msg = "All ships placed! Waiting for opponent..."
            self.status_var.set(msg)
        elif self.game_phase == 'Attack':
            if self.my_turn:
                self.status_var.set("Your Turn: Fire a shot on the RED board.")
            else:
                self.status_var.set("Opponent's Turn... Please wait.")
        elif self.game_phase == "Waiting":
            self.status_var.set("Waiting for opponent...")

    def on_closing(self):
        if self.sock:
            self.sock.close()
        self.destroy()
        sys.exit()


# ---
# ---
# --- MAIN MENU LAUNCHER ---
# ---
# ---

class MainMenu(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Battleship - Main Menu")
        self.geometry("450x300")

        label = tk.Label(self, text="BATTLESHIP", font=('Arial', 24, 'bold'))
        label.pack(pady=20)

        label_choose = tk.Label(self, text="Choose Your Game Mode", font=('Arial', 16))
        label_choose.pack(pady=10)

        pvp_button = tk.Button(self, text="Play Online (PvP)", font=('Arial', 14), command=self.launch_pvp, height=2)
        pvp_button.pack(pady=10, padx=20, fill='x')

        pve_button = tk.Button(self, text="Play vs. Bot (PvE)", font=('Arial', 14), command=self.launch_pve, height=2)
        pve_button.pack(pady=10, padx=20, fill='x')

    def launch_pvp(self):
        """Launches the online client."""
        # This menu (self) is a valid parent for the dialog
        host_ip = simpledialog.askstring(
            "Connect to Server",
            "Enter the Host's IP address:",
            parent=self
        )

        if host_ip:
            self.destroy()
            game = BattleshipGame_Client(host_ip)
            game.mainloop()
        # If they cancel, do nothing and leave the menu open

    def launch_pve(self):
        """Launches the local bot game."""
        self.destroy()
        game = BattleshipGame_PvE()
        game.mainloop()


# --- Run the Game ---
if __name__ == "__main__":
    # We no longer need a temporary root, because the MainMenu
    # itself can act as the parent for the simpledialog.
    menu = MainMenu()
    menu.mainloop()