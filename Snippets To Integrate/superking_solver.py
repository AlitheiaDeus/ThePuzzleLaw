# puzzles/solver/superking_solver.py
#
# Author: AlitheiaDeus & Gemini
# Date: 2025-08-28
#
# An interactive puzzle for solving the N-Superking problem with zones.
# A "Superking" attacks like a chess rook and a king combined.

import tkinter as tk
from tkinter import font, messagebox
import random
from collections import deque

# --- Conditional Import for Numpy ---
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False
    print("Warning: Numpy not found. Superking solver will use a slower list-based implementation.")


class SuperkingSolverApp(tk.Frame):
    """An interactive puzzle for solving the N-Superking problem with zones."""
    def __init__(self, master, show_main_menu_callback):
        super().__init__(master, bg="#2E2E2E")
        self.show_main_menu_callback = show_main_menu_callback
        self.show_start_menu()

    def stop_game_loop(self):
        """Stops the solver if it's running."""
        self.solver_running = False

    def _clear_container(self):
        for widget in self.winfo_children():
            widget.destroy()

    def show_start_menu(self):
        self._reset_game_state()
        self._clear_container()
        menu_frame = tk.Frame(self, bg="#2E2E2E")
        menu_frame.pack(expand=True)
        tk.Label(menu_frame, text="N-Superking Solver", font=("Helvetica", 24, "bold"), bg="#2E2E2E", fg="white").pack(pady=(40, 20))
        input_frame = tk.Frame(menu_frame, bg="#2E2E2E")
        input_frame.pack(pady=20)
        tk.Label(input_frame, text="Enter board size (N):", font=("Helvetica", 14), bg="#2E2E2E", fg="white").pack(side="left", padx=(0, 10))
        self.n_entry = tk.Entry(input_frame, font=("Helvetica", 14), width=5, justify="center", bg="#3C3C3C", fg="white", insertbackground="white", relief="flat")
        self.n_entry.pack(side="left")
        self.n_entry.focus_set()
        self.n_entry.bind("<Return>", lambda e: self.process_input())
        tk.Button(input_frame, text="Go", font=("Helvetica", 12), command=self.process_input, bg="#4A4A4A", fg="white", relief="flat").pack(side="left", padx=(10, 0))
        self.error_label = tk.Label(menu_frame, text="", font=("Helvetica", 10), bg="#2E2E2E", fg="#FF5555")
        self.error_label.pack(pady=5)
        tk.Button(menu_frame, text="Back to Menu", font=("Helvetica", 14), command=self.show_main_menu_callback, bg="#4A4A4A", fg="white", relief="flat").pack(pady=40)

    def _reset_game_state(self):
        self.n = 0
        self.zones = []
        self.cell_to_zone_map = None
        self.current_zone_index = 0
        self.current_zone_cells = []
        self.solver_running = False
        self.solution_found = False
        self.board = None
        self.solver_generator = None
        # State variables for robust drag handling
        self.drag_mode = None # Can be 'paint', 'erase', or None
        self._last_drag_cell = None

    def process_input(self):
        try:
            n = int(self.n_entry.get())
            if n > 0:
                if not NUMPY_AVAILABLE and n > 8:
                    self.error_label.config(text="Without numpy, N > 8 is very slow. Proceed with caution.")
                else:
                    self.error_label.config(text="")
                self.start_game(n)
            else:
                self.error_label.config(text="Please enter a positive number.")
        except ValueError:
            self.error_label.config(text="Invalid input. Please enter an integer.")

    def start_game(self, n):
        self.n = n
        self.zones = [[] for _ in range(n)]
        if NUMPY_AVAILABLE:
            self.cell_to_zone_map = np.full((n, n), -1, dtype=int)
        else:
            self.cell_to_zone_map = [[-1 for _ in range(n)] for _ in range(n)]
        self.current_zone_index = 0
        self.current_zone_cells = []
        self.zone_colors = self._generate_colors(n)
        self.show_game_board()

    def _generate_colors(self, num_colors):
        bright_palette = ["#FF3333", "#3399FF", "#33CC33", "#FFFF33", "#FF66CC", "#66FFFF", "#FF9933", "#9966FF", "#00FF99", "#FF6666", "#33CCCC", "#CCFF33", "#CC33FF", "#FFCC33", "#3366FF"]
        if num_colors <= len(bright_palette):
            return bright_palette[:num_colors]
        else:
            return ["#"+''.join([random.choice('0123456789ABCDEF') for _ in range(6)]) for _ in range(num_colors)]

    def show_game_board(self):
        self._clear_container()
        cell_size = max(30, 600 // (self.n + 1))
        main_game_frame = tk.Frame(self, bg="#2E2E2E")
        main_game_frame.pack(expand=True, padx=10, pady=10)
        self.board_frame = tk.Frame(main_game_frame, bg="#1E1E1E")
        self.board_frame.grid(row=0, column=0, padx=(0, 20))
        self.board_cells = [[None for _ in range(self.n)] for _ in range(self.n)]
        
        for r in range(self.n):
            for c in range(self.n):
                canvas = tk.Canvas(self.board_frame, width=cell_size, height=cell_size, bg="#3C3C3C", highlightbackground="#555555", highlightthickness=1, bd=0)
                canvas.grid(row=r, column=c)
                # Cell only listens for the initial click down
                canvas.bind("<Button-1>", lambda e, r=r, c=c: self.handle_mouse_down(r, c))
                # Right-click is a simple, stateless action
                canvas.bind("<Button-3>", lambda e: self.handle_right_click())
                self.board_cells[r][c] = canvas
        
        side_panel = tk.Frame(main_game_frame, bg="#2E2E2E")
        side_panel.grid(row=0, column=1, sticky="N")
        tk.Label(side_panel, text="Zones", font=("Helvetica", 14, "bold"), bg="#2E2E2E", fg="white").pack(pady=(0, 10))
        self.zone_indicators = []
        for i in range(self.n):
            indicator = tk.Frame(side_panel, width=40, height=20, bg=self.zone_colors[i], highlightbackground="white", highlightthickness=0, cursor="hand2")
            indicator.pack(pady=2)
            indicator.bind("<Button-1>", lambda e, index=i: self.set_current_zone(index))
            self.zone_indicators.append(indicator)
        self.update_zone_indicator()
        
        action_frame = tk.Frame(side_panel, bg="#2E2E2E")
        action_frame.pack(pady=20)
        self.solve_button = tk.Button(action_frame, text="Solve", command=self.solve_puzzle, bg="#4CAF50", fg="white", relief="flat", font=("Helvetica", 12, "bold"), state=tk.DISABLED)
        self.solve_button.pack(pady=5, fill='x')
        self.reset_button = tk.Button(action_frame, text="Reset Zones", command=self.reset_board, bg="#FF6B6B", fg="white", relief="flat", font=("Helvetica", 11))
        self.reset_button.pack(pady=5, fill='x')
        
        tk.Button(action_frame, text="New Size", command=self.show_start_menu, bg="#3399FF", fg="white", relief="flat", font=("Helvetica", 11)).pack(pady=5, fill='x')
        tk.Button(action_frame, text="Back to Menu", command=self.show_main_menu_callback, bg="#4A4A4A", fg="white", relief="flat", font=("Helvetica", 11)).pack(pady=5, fill='x')

        self.new_game_button = tk.Button(action_frame, text="New Game", command=self.show_start_menu, bg="#3399FF", fg="white", relief="flat", font=("Helvetica", 11))

        self.status_label = tk.Label(side_panel, text="", font=("Helvetica", 10, "italic"), bg="#2E2E2E", fg="lightgreen")
        self.status_label.pack(pady=10)

    def reset_board(self):
        if self.solver_running: return
        self.start_game(self.n)

    def set_current_zone(self, zone_index):
        if self.solver_running: return
        if self.current_zone_cells:
            self.zones[self.current_zone_index] = list(self.current_zone_cells)
            for r, c in self.current_zone_cells: self.cell_to_zone_map[r][c] = self.current_zone_index
        
        cells_to_edit = self.zones[zone_index]
        if cells_to_edit:
            self.zones[zone_index] = []
            for r, c in cells_to_edit: self.cell_to_zone_map[r][c] = -1
        
        self.current_zone_cells = list(cells_to_edit)
        self.current_zone_index = zone_index
        self.update_zone_indicator()
        self.check_completion()

    # --- Reassessed and Robust Mouse Handling ---
    def handle_mouse_down(self, row, col):
        """Called on click. Sets mode and applies action to the first cell."""
        if self.solver_running: return

        cell_coords = (row, col)
        if cell_coords in self.current_zone_cells:
            self.drag_mode = 'erase'
        elif self.cell_to_zone_map[row][col] == -1:
            self.drag_mode = 'paint'
        else:
            self.drag_mode = None

        self._apply_drag_action(row, col)
        self._last_drag_cell = (row, col)

        # Temporarily bind drag and release to the parent frame to capture global motion
        self.board_frame.bind("<B1-Motion>", self.handle_mouse_drag)
        self.board_frame.bind("<ButtonRelease-1>", self.handle_mouse_up)

    def handle_mouse_drag(self, event):
        """Called on motion. Calculates cell from event and applies action."""
        if self.drag_mode is None: return

        # Get cell dimensions on the fly
        cell_w = self.board_cells[0][0].winfo_width()
        cell_h = self.board_cells[0][0].winfo_height()
        if cell_w == 0 or cell_h == 0: return # Avoid division by zero if not rendered

        # Calculate row and col from the event's coordinates relative to the board_frame
        col = event.x // cell_w
        row = event.y // cell_h

        if 0 <= row < self.n and 0 <= col < self.n:
            current_cell = (row, col)
            # Only apply action if we've moved to a new cell to avoid redundant calls
            if current_cell != self._last_drag_cell:
                self._apply_drag_action(row, col)
                self._last_drag_cell = current_cell

    def handle_mouse_up(self, event):
        """Called on release. Clears state and unbinds temporary events."""
        self.drag_mode = None
        self._last_drag_cell = None
        
        # Unbind from the parent frame to stop listening for drag/release
        self.board_frame.unbind("<B1-Motion>")
        self.board_frame.unbind("<ButtonRelease-1>")

    def _apply_drag_action(self, row, col):
        """Applies the current drag mode (paint or erase) to a cell."""
        if self.drag_mode == 'paint':
            self._paint_cell(row, col)
        elif self.drag_mode == 'erase':
            self._erase_cell(row, col)

    def _paint_cell(self, row, col):
        """Adds a cell to the current zone if it's empty."""
        if self.current_zone_index >= self.n: return
        cell_coords = (row, col)
        if self.cell_to_zone_map[row][col] == -1 and cell_coords not in self.current_zone_cells:
            self.current_zone_cells.append(cell_coords)
            self.board_cells[row][col].config(bg=self.zone_colors[self.current_zone_index])
            self.check_completion()
    
    def _erase_cell(self, row, col):
        """Removes a cell from the current zone."""
        cell_coords = (row, col)
        if cell_coords in self.current_zone_cells:
            self.current_zone_cells.remove(cell_coords)
            self.board_cells[row][col].config(bg="#3C3C3C")
            self.check_completion()

    def handle_right_click(self, event=None):
        """Commits the current zone and cycles to the next available one."""
        if self.current_zone_index >= self.n or self.solver_running: return
        
        if self.current_zone_cells:
            self.zones[self.current_zone_index] = list(self.current_zone_cells)
            for r, c in self.current_zone_cells:
                self.cell_to_zone_map[r][c] = self.current_zone_index
            self.current_zone_cells.clear()
        
        start_search = (self.current_zone_index + 1) % self.n
        for i in range(self.n):
            idx = (start_search + i) % self.n
            if not self.zones[idx]:
                self.current_zone_index = idx
                self.update_zone_indicator()
                self.check_completion()
                return
        
        self.current_zone_index = self.n
        self.update_zone_indicator()
        self.check_completion()

    def update_zone_indicator(self):
        for i, indicator in enumerate(self.zone_indicators):
            indicator.config(highlightthickness=2 if i == self.current_zone_index else 0)

    def check_completion(self):
        defined_zones = [z for z in self.zones if z]
        all_defined = len(defined_zones) == self.n and not self.current_zone_cells
        
        self.solve_button.config(state=tk.NORMAL if all_defined else tk.DISABLED)
        self.status_label.config(text="All zones set!" if all_defined else "")

    def _is_zone_contiguous(self, zone):
        if not zone or len(zone) == 1: return True
        q, visited, zone_set = deque([zone[0]]), {zone[0]}, set(zone)
        while q:
            r, c = q.popleft()
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                neighbor = (r + dr, c + dc)
                if neighbor in zone_set and neighbor not in visited:
                    visited.add(neighbor)
                    q.append(neighbor)
        return len(visited) == len(zone)

    def solve_puzzle(self):
        self.handle_right_click()

        if sum(len(z) for z in self.zones) != self.n * self.n:
            messagebox.showerror("Error", f"Expected {self.n*self.n} zoned cells, but found {sum(len(z) for z in self.zones)}.")
            return
        for i, zone in enumerate(self.zones):
            if not self._is_zone_contiguous(zone):
                messagebox.showerror("Error", f"Zone {i+1} (color: {self.zone_colors[i]}) is not contiguous.")
                return

        self.solver_running = True
        self.solution_found = False
        self.solve_button.pack_forget()
        self.reset_button.pack_forget()
        
        self.board = [[0 for _ in range(self.n)] for _ in range(self.n)]
        for r in range(self.n):
            for c in range(self.n):
                self.board_cells[r][c].delete("all")
        
        self.solver_generator = self._solver_step(0)
        self.after(10, self._run_solver_step)

    def _on_solver_finish(self):
        self.solver_running = False
        if self.solution_found:
            self.status_label.config(text="Solution Found!", fg="lightgreen")
        else:
            self.status_label.config(text="No solution found.", fg="#FF5555")
        self.reset_button.pack(pady=5, fill='x')
        self.new_game_button.pack(pady=5, fill='x')

    def _run_solver_step(self):
        try:
            for _ in range(self.n * 2):
                if not self.solver_running: break
                next(self.solver_generator)
            
            if self.solver_running:
                self.after(1, self._run_solver_step)
        except StopIteration:
            self._on_solver_finish()

    def _update_cell_display(self, r, c, is_queen):
        canvas = self.board_cells[r][c]
        canvas.delete("all")
        if is_queen:
            cell_size = canvas.winfo_width()
            center_x, center_y = cell_size / 2, cell_size / 2
            star_font = font.Font(family="Arial", size=int(cell_size * 0.6), weight="bold")
            canvas.create_text(center_x, center_y, text="★", fill="white", font=star_font)

    def _is_safe(self, row, col):
        # Check Rook attacks
        for i in range(self.n):
            if self.board[row][i] == 1 or self.board[i][col] == 1:
                return False
        # Check King attacks
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0: continue
                nr, nc = row + dr, col + dc
                if 0 <= nr < self.n and 0 <= nc < self.n and self.board[nr][nc] == 1:
                    return False

        # Check for another queen in the same custom zone
        zone_idx = self.cell_to_zone_map[row][col]
        if zone_idx != -1: # Ensure zone index is valid
            for r_z, c_z in self.zones[zone_idx]:
                if self.board[r_z][c_z] == 1:
                    return False
                
        return True

    def _solver_step(self, col):
        if col >= self.n:
            self.solution_found = True
            yield True
            return

        for i in range(self.n):
            if not self.solver_running: return
            
            yield
            if self._is_safe(i, col):
                self.board[i][col] = 1
                self._update_cell_display(i, col, True)
                
                yield
                # Recurse
                sub_solver = self._solver_step(col + 1)
                try:
                    while True:
                        next(sub_solver)
                        if self.solution_found:
                            yield True
                            return
                        yield
                except StopIteration:
                    pass
                
                # Backtrack
                self.board[i][col] = 0
                self._update_cell_display(i, col, False)
        yield False
