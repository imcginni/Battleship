import tkinter as tk

# --- Configuration ---
GRID_SIZE = 10
SQUARE_SIZE = 40
CANVAS_SIZE = SQUARE_SIZE * GRID_SIZE
SHIP_SIZES = [5, 4, 3, 3, 2]
SHIP_COLORS = {
    5: "purple",
    4: "orange",
    3: "yellow",
    2: "green",
    1: "blue"
}


# --- Game State Class ---
class PlayerBoard:
    """Manages the state and data for a single player's board."""

    def __init__(self, name):
        self.name = name
        self.ships = []
        self.grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.shots_fired = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.ships_placed_count = 0
        self.ships_sunk_count = 0
        self.current_ship_index = 0

    def add_ship(self, size, col, row, orientation):
        """Adds a ship to the board and updates the grid."""
        # Note: In the network version, the client GUI will do this
        # and the server will validate and store it.
        self.ships.append({
            'size': size,
            'col': col,
            'row': row,
            'orientation': orientation,
            'hits': 0
        })
        for i in range(size):
            r = row + i if orientation == 'V' else row
            c = col + i if orientation == 'H' else col
            self.grid[r][c] = 1
        self.ships_placed_count += 1
        self.current_ship_index += 1

    def receive_shot(self, col, row):
        """Processes an incoming shot and returns 'Hit' or 'Miss'."""
        if self.grid[row][col] == 1:
            self.grid[row][col] = 'H'  # Mark as Hit

            for ship in self.ships:
                r_start, c_start = ship['row'], ship['col']
                s_size, s_orient = ship['size'], ship['orientation']

                is_this_ship = False
                if s_orient == 'H' and r_start == row and c_start <= col < c_start + s_size:
                    is_this_ship = True
                elif s_orient == 'V' and c_start == col and r_start <= row < r_start + s_size:
                    is_this_ship = True

                if is_this_ship:
                    ship['hits'] += 1
                    if ship['hits'] == s_size:
                        self.ships_sunk_count += 1
                        return 'Sunk', True
                    return 'Hit', False

            return 'Hit', False
        else:
            self.grid[row][col] = 'M'
            return 'Miss', False

    def is_valid_placement(self, size, col, row, orientation):
        """Checks for boundary and collision."""
        end_col = col + (size - 1) if orientation == 'H' else col
        end_row = row + (size - 1) if orientation == 'V' else row

        if not (0 <= col < GRID_SIZE and 0 <= row < GRID_SIZE and
                0 <= end_col < GRID_SIZE and 0 <= end_row < GRID_SIZE):
            return False

        for i in range(size):
            r = row + i if orientation == 'V' else row
            c = col + i if orientation == 'H' else col
            if self.grid[r][c] != 0:
                return False
        return True


# --- Utility Drawing Functions (for client) ---
def draw_grid_lines(canvas):
    """Draws the 10x10 grid lines and coordinates."""
    canvas.delete("grid_lines")
    for i in range(GRID_SIZE + 1):
        coord = i * SQUARE_SIZE
        canvas.create_line(0, coord, CANVAS_SIZE, coord, fill="gray", tags="grid_lines")
        canvas.create_line(coord, 0, coord, CANVAS_SIZE, fill="gray", tags="grid_lines")

    for i in range(GRID_SIZE):
        center = i * SQUARE_SIZE + SQUARE_SIZE // 2
        canvas.create_text(center, -15, text=chr(ord('A') + i), font=('Arial', 10, 'bold'), tags="grid_lines")
        canvas.create_text(-15, center, text=str(i + 1), font=('Arial', 10, 'bold'), tags="grid_lines")

    canvas.configure(scrollregion=(-25, -25, CANVAS_SIZE + 5, CANVAS_SIZE + 5))


def draw_hit_marker(canvas, c, r):
    x1 = c * SQUARE_SIZE
    y1 = r * SQUARE_SIZE
    x2 = x1 + SQUARE_SIZE
    y2 = y1 + SQUARE_SIZE
    canvas.create_line(x1 + 5, y1 + 5, x2 - 5, y2 - 5, fill='red', width=5)
    canvas.create_line(x1 + 5, y2 - 5, x2 - 5, y1 + 5, fill='red', width=5)


def draw_miss_marker(canvas, c, r):
    x_center = c * SQUARE_SIZE + SQUARE_SIZE // 2
    y_center = r * SQUARE_SIZE + SQUARE_SIZE // 2
    R = SQUARE_SIZE // 6
    canvas.create_oval(x_center - R, y_center - R, x_center + R, y_center + R, fill='white', outline='darkblue',
                       width=2)