# puzzles/solver/chess_attack_solver.py
#
# Author: AlitheiaDeus & Gemini
# Date: 2025-08-31
#
# An interactive, heuristic-based solver for N-piece chess problems on a
# customizable, zoned board. It uses a combination of logical deduction and
# backtracking to find solutions for pieces like Queens and Superkings.

import tkinter as tk
from tkinter import font
import random
from collections import deque
from itertools import combinations

class ChessAttackSolverApp(tk.Frame):
    """
    An interactive application for defining and solving zoned N-piece chess
    puzzles using heuristic-driven logic and visualization.
    """
    def __init__(self, master, show_main_menu_callback):
        super().__init__(master, bg="#2E2E2E")
        self.show_main_menu_callback = show_main_menu_callback
        
        # --- Core Application State ---
        self.n = 0
        self.piece_type = "Superking" # Default piece
        self.piece_symbols = {"Queen": "♕", "Superking": "♔"}
        
        # --- Board and Solver State ---
        # 0=empty, 1=piece (temporary or confirmed)
        self.board_state = []
        # Counts how many pieces attack each cell
        self.attack_map = []
        # 0=normal, 1=confirmed piece, -1=confirmed empty via heuristics
        self.deduction_map = []
        self.solver_running = False
        self.solver_generator = None
        self.cell_size = 50

        # --- Zone-related State ---
        self.zones = [] # List of lists, storing (r, c) for each zone
        self.cell_to_zone_map = [] # 2D grid mapping each cell to a zone index
        self.current_zone_index = 0 # The zone being actively painted
        self.zone_colors = []
        self.zone_indicators = []
        self._last_drag_cell = None # Used to prevent redundant calls during drag-painting
        
        self.show_start_menu()

    def stop_game_loop(self):
        """Stops the solver visualization if it's running."""
        self.solver_running = False

    def _clear_container(self):
        """Removes all widgets from the main frame to prepare for a new view."""
        for widget in self.winfo_children():
            widget.destroy()

    # --- UI Navigation ---

    def show_start_menu(self):
        """Displays the initial menu to get the board size and piece type."""
        self._clear_container()
        self.stop_game_loop()

        menu_frame = tk.Frame(self, bg="#2E2E2E")
        menu_frame.pack(expand=True)
        
        tk.Label(menu_frame, text="Chess Attack Solver", font=("Helvetica", 24, "bold"), bg="#2E2E2E", fg="white").pack(pady=(40, 10))
        
        # --- Board Size Input ---
        input_frame = tk.Frame(menu_frame, bg="#2E2E2E")
        input_frame.pack(pady=10)
        tk.Label(input_frame, text="Board Size (N):", font=("Helvetica", 14), bg="#2E2E2E", fg="white").pack(side="left", padx=(0, 10))
        self.n_entry = tk.Entry(input_frame, font=("Helvetica", 14), width=5, justify="center", bg="#3C3C3C", fg="white", insertbackground="white", relief="flat")
        self.n_entry.pack(side="left")
        self.n_entry.focus_set()
        self.n_entry.bind("<Return>", self._process_input)
        
        # --- Piece Type Selection ---
        tk.Label(menu_frame, text="Select Piece Type", font=("Helvetica", 14), bg="#2E2E2E", fg="white").pack(pady=(20, 5))
        
        self.piece_type_var = tk.StringVar(value=self.piece_type)
        radio_frame = tk.Frame(menu_frame, bg="#2E2E2E")
        radio_frame.pack(pady=5)
        
        style_args = {"bg": "#2E2E2E", "fg": "white", "selectcolor": "#4A4A4A", 
                      "activebackground": "#2E2E2E", "activeforeground": "white",
                      "highlightthickness": 0, "font": ("Helvetica", 12), "pady": 5}

        tk.Radiobutton(radio_frame, text="Queen (Rook + Bishop)", variable=self.piece_type_var, value="Queen", **style_args).pack(anchor="w")
        tk.Radiobutton(radio_frame, text="Superking (Rook + King)", variable=self.piece_type_var, value="Superking", **style_args).pack(anchor="w")

        # --- Action Buttons ---
        tk.Button(menu_frame, text="Define Zones", font=("Helvetica", 14, "bold"), command=self._process_input, bg="#4CAF50", fg="white", relief="flat", padx=20, pady=10).pack(pady=20)
        
        self.error_label = tk.Label(menu_frame, text="", font=("Helvetica", 10), bg="#2E2E2E", fg="#FF5555")
        self.error_label.pack(pady=5)
        
        tk.Button(menu_frame, text="Back to Menu", font=("Helvetica", 12), command=self.show_main_menu_callback, bg="#4A4A4A", fg="white", relief="flat").pack(pady=(10, 40))

    def show_game_board(self):
        """Creates and displays the main board UI for zone definition."""
        self._clear_container()
        self._initialize_zone_state()
        
        self.cell_size = max(30, 600 // (self.n + 1))
        
        main_game_frame = tk.Frame(self, bg="#2E2E2E")
        main_game_frame.pack(expand=True, padx=10, pady=10)
        
        # --- Board ---
        self.board_frame = tk.Frame(main_game_frame, bg="#1E1E1E")
        self.board_frame.grid(row=0, column=0, padx=(0, 20))
        self.board_frame.bind("<Button-3>", self._cycle_zone)
        
        self.board_cells = [[None for _ in range(self.n)] for _ in range(self.n)]
        for r in range(self.n):
            for c in range(self.n):
                canvas = tk.Canvas(self.board_frame, width=self.cell_size, height=self.cell_size, 
                                   highlightthickness=1, highlightbackground="#1E1E1E", bd=0)
                canvas.grid(row=r, column=c)
                canvas.bind("<Button-1>", lambda e, r=r, c=c: self._handle_mouse_down(e, r, c))
                canvas.bind("<Button-3>", self._cycle_zone)
                self.board_cells[r][c] = canvas
        
        self._draw_board()

        # --- Side Panel ---
        side_panel = tk.Frame(main_game_frame, bg="#2E2E2E")
        side_panel.grid(row=0, column=1, sticky="N")
        
        # --- Zone Indicators ---
        tk.Label(side_panel, text="Zones", font=("Helvetica", 14, "bold"), bg="#2E2E2E", fg="white").pack(pady=(0, 10))
        self.zone_indicators = []
        for i in range(self.n):
            indicator = tk.Frame(side_panel, width=40, height=20, bg=self.zone_colors[i], highlightbackground="white", highlightthickness=0, cursor="hand2")
            indicator.pack(pady=2)
            indicator.bind("<Button-1>", lambda e, index=i: self._set_current_zone(index))
            self.zone_indicators.append(indicator)
        self._update_zone_indicator_ui()

        # --- Action Buttons ---
        action_frame = tk.Frame(side_panel, bg="#2E2E2E")
        action_frame.pack(pady=20)
        
        self.solve_button = tk.Button(action_frame, text="Solve!", command=self.solve_puzzle, bg="#4CAF50", fg="white", relief="flat", font=("Helvetica", 12, "bold"), state=tk.DISABLED)
        self.solve_button.pack(pady=5, fill='x')

        self.reset_zones_button = tk.Button(action_frame, text="Reset Zones", command=self._reset_zones, bg="#FF6B6B", fg="white", relief="flat", font=("Helvetica", 11))
        self.reset_zones_button.pack(pady=5, fill='x')
        
        tk.Button(action_frame, text="New Game", command=self.show_start_menu, bg="#3399FF", fg="white", relief="flat", font=("Helvetica", 11)).pack(pady=(20, 5), fill='x')
        tk.Button(action_frame, text="Back to Menu", command=self.show_main_menu_callback, bg="#4A4A4A", fg="white", relief="flat", font=("Helvetica", 11)).pack(pady=5, fill='x')

        self.status_label = tk.Label(side_panel, text=f"{self.n*self.n} cells to zone.", font=("Helvetica", 10, "italic"), bg="#2E2E2E", fg="yellow", wraplength=150)
        self.status_label.pack(pady=10)

    # --- Game Logic & State Management ---

    def _process_input(self, event=None):
        """Validates user input from the start menu and proceeds to the board."""
        try:
            n_val = int(self.n_entry.get())
            if 1 <= n_val <= 20: # Limit size for performance and UI stability
                self.n = n_val
                self.piece_type = self.piece_type_var.get()
                self.show_game_board()
            else:
                self.error_label.config(text="Please enter a number between 1 and 20.")
        except ValueError:
            self.error_label.config(text="Invalid input. Please enter an integer.")
    
    def _draw_board(self):
        """
        Updates the entire visual representation of the board based on the
        current state maps (board_state, attack_map, deduction_map).
        """
        piece_font = font.Font(family="Helvetica", size=int(self.cell_size * 0.6), weight="bold")

        for r in range(self.n):
            for c in range(self.n):
                canvas = self.board_cells[r][c]
                zone_idx = self.cell_to_zone_map[r][c]
                
                # Set background color based on zone or checkerboard pattern
                bg_color = self.zone_colors[zone_idx] if zone_idx != -1 else ("#C0C0C0" if (r + c) % 2 == 0 else "#606060")
                canvas.config(bg=bg_color)
                canvas.delete("all")

                is_piece = self.board_state and self.board_state[r][c] == 1
                deduction_state = self.deduction_map[r][c] if self.deduction_map else 0

                # 1. Draw temporary attacks ("thoughts") from backtracking
                if self.attack_map and self.attack_map[r][c] > 0 and not is_piece:
                    padding = self.cell_size * 0.35
                    canvas.create_rectangle(padding, padding, self.cell_size - padding, self.cell_size - padding, 
                                            fill="#555555", outline="")
                
                # 2. Draw confirmed empty markers from heuristics
                if deduction_state == -1:
                    padding = self.cell_size * 0.3
                    canvas.create_line(padding, padding, self.cell_size - padding, self.cell_size - padding, fill="#FF5555", width=2)
                    canvas.create_line(padding, self.cell_size - padding, self.cell_size - padding, padding, fill="#FF5555", width=2)

                # 3. Draw pieces on top of everything else
                if is_piece:
                    # Draw a highlight circle for pieces confirmed by heuristics
                    if deduction_state == 1:
                        padding = self.cell_size * 0.1
                        canvas.create_oval(padding, padding, self.cell_size - padding, self.cell_size - padding, 
                                           fill="#00C851", outline="")

                    symbol = self.piece_symbols.get(self.piece_type, "?")
                    canvas.create_text(self.cell_size / 2, self.cell_size / 2, text=symbol, 
                                       fill="white", font=piece_font)

    # --- Zone Definition Logic ---

    def _initialize_zone_state(self):
        """Sets up/resets all data structures for a new zone-definition session."""
        self.board_state = [[0 for _ in range(self.n)] for _ in range(self.n)]
        self.attack_map = [[0 for _ in range(self.n)] for _ in range(self.n)]
        self.deduction_map = [[0 for _ in range(self.n)] for _ in range(self.n)]
        self.zones = [[] for _ in range(self.n)]
        self.cell_to_zone_map = [[-1 for _ in range(self.n)] for _ in range(self.n)]
        self.current_zone_index = 0
        self.zone_colors = self._generate_zone_colors()
        self.solver_running = False

    def _generate_zone_colors(self):
        """Generates N visually distinct, bright colors for the zones."""
        bright_palette = [
            "#FF3333",  # Red
            "#3399FF",  # Blue
            "#33CC33",  # Green
            "#FFFF33",  # Yellow
            "#FF66CC",  # Pink
            "#66FFFF",  # Cyan
            "#FF9933",  # Orange
            "#9966FF",  # Purple
            "#FF7F50",  # Coral
            "#20B2AA",  # Light Sea Green
            "#DDA0DD",  # Plum
            "#3CB371",  # Medium Sea Green
        ]
        if self.n <= len(bright_palette):
            return bright_palette[:self.n]
        # Fallback to random colors for N > 12
        return ["#"+''.join([random.choice('89ABCDEF') for _ in range(6)]) for _ in range(self.n)]

    def _reset_zones(self):
        """Clears all user-defined zones from the board."""
        if self.solver_running: return
        self._initialize_zone_state()
        
        # Update indicator colors to match the new self.zone_colors list
        for i, indicator in enumerate(self.zone_indicators):
            indicator.config(bg=self.zone_colors[i])

        self._draw_board()
        self.solve_button.config(state=tk.DISABLED)
        self.status_label.config(text=f"{self.n*self.n} cells to zone.", fg="yellow")

    def _handle_mouse_down(self, event, r, c):
        """Initiates the drag-painting process on a cell."""
        if self.solver_running: return
        self._paint_cell(r, c)
        self._last_drag_cell = (r, c)
        self.board_frame.bind("<B1-Motion>", self._handle_mouse_drag)
        self.board_frame.bind("<ButtonRelease-1>", self._handle_mouse_up)

    def _handle_mouse_drag(self, event):
        """Continues painting as the mouse is dragged over new cells."""
        if self.solver_running: return
        col = event.x // self.cell_size
        row = event.y // self.cell_size
        if 0 <= row < self.n and 0 <= col < self.n:
            current_cell = (row, col)
            if current_cell != self._last_drag_cell:
                self._paint_cell(row, col)
                self._last_drag_cell = current_cell
    
    def _handle_mouse_up(self, event):
        """Finalizes the drag-painting process."""
        self._last_drag_cell = None
        self.board_frame.unbind("<B1-Motion>")
        self.board_frame.unbind("<ButtonRelease-1>")

    def _paint_cell(self, r, c):
        """Assigns a cell to the current zone, overwriting if it belongs to another."""
        old_zone = self.cell_to_zone_map[r][c]
        if old_zone == self.current_zone_index: return # Already in the correct zone

        # If the cell was part of another zone, remove it from there first
        if old_zone != -1:
            self.zones[old_zone].remove((r, c))
        
        self.zones[self.current_zone_index].append((r, c))
        self.cell_to_zone_map[r][c] = self.current_zone_index
        
        self.board_cells[r][c].config(bg=self.zone_colors[self.current_zone_index])
        self._check_completion()

    def _set_current_zone(self, index):
        """Sets the active zone for painting, triggered by the side panel."""
        if self.solver_running: return
        self.current_zone_index = index
        self._update_zone_indicator_ui()

    def _cycle_zone(self, event):
        """Cycles to the next un-started zone, triggered by right-clicking."""
        if self.solver_running: return
        start_idx = (self.current_zone_index + 1) % self.n
        # Find the next zone that has no cells assigned to it yet
        for i in range(self.n):
            check_idx = (start_idx + i) % self.n
            if not self.zones[check_idx]:
                self._set_current_zone(check_idx)
                return
        self._set_current_zone(start_idx) # Fallback if all zones have cells

    def _update_zone_indicator_ui(self):
        """Highlights the currently selected zone in the side panel."""
        for i, indicator in enumerate(self.zone_indicators):
            indicator.config(highlightthickness=2 if i == self.current_zone_index else 0)

    def _check_completion(self):
        """
        Checks if all cells are zoned. If so, validates the zones and enables
        the solve button if they are valid.
        """
        unzoned_count = sum(row.count(-1) for row in self.cell_to_zone_map)
        
        if unzoned_count > 0:
            self.status_label.config(text=f"{unzoned_count} cells to zone.", fg="yellow")
            self.solve_button.config(state=tk.DISABLED)
            return

        # All cells are zoned, now validate the zone structures
        all_zones_valid, error_msg = self._validate_zones()
        if all_zones_valid:
            self.status_label.config(text="All zones valid. Ready to solve!", fg="lightgreen")
            self.solve_button.config(state=tk.NORMAL)
        else:
            self.status_label.config(text=error_msg, fg="#FF5555")
            self.solve_button.config(state=tk.DISABLED)

    def _validate_zones(self):
        """Ensures all N zones are non-empty and contiguous."""
        for i in range(self.n):
            zone_cells = self.zones[i]
            if not zone_cells:
                return False, f"Error: Zone {i+1} is empty."
            if not self._is_contiguous(zone_cells):
                return False, f"Error: Zone {i+1} is not contiguous."
        return True, ""

    def _is_contiguous(self, zone_cells):
        """
        Checks if a set of cells forms a single connected component using a
        Breadth-First Search (BFS).
        """
        if not zone_cells: return True
        
        q, visited = deque([zone_cells[0]]), {zone_cells[0]}
        zone_set = set(zone_cells)
        
        while q:
            r, c = q.popleft()
            # Check orthogonal neighbors
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                neighbor = (r + dr, c + dc)
                if neighbor in zone_set and neighbor not in visited:
                    visited.add(neighbor)
                    q.append(neighbor)
        # The zone is contiguous if the number of visited cells equals the total
        return len(visited) == len(zone_cells)


    # --- Solver Logic ---

    def solve_puzzle(self):
        """
        The main entry point for the solver. Resets state and starts the
        solver generator.
        """
        if self.solver_running: return
        
        # Reset state from any previous run
        self.board_state = [[0 for _ in range(self.n)] for _ in range(self.n)]
        self.deduction_map = [[0 for _ in range(self.n)] for _ in range(self.n)]
        self._update_attack_map()
        self._draw_board()

        self.solver_running = True
        self.status_label.config(text=f"Solving for {self.n}-{self.piece_type}s...", fg="yellow")
        self.solve_button.config(state=tk.DISABLED)
        self.reset_zones_button.config(state=tk.DISABLED)
        
        # The solver is a generator to allow for step-by-step visualization
        self.solver_generator = self._solver_entry_point()
        self._run_solver_step()

    def _run_solver_step(self):
        """
        Executes steps of the solver generator and schedules the next run.
        This creates the animated "thinking" process.
        """
        if not self.solver_running: return
        
        try:
            # Execute multiple non-visual steps for speed, then one visual step
            for _ in range(10): 
                # A `False` yield means a non-visual step (no change to draw)
                if not next(self.solver_generator): break
            
            # A `True` yield means a visual change occurred
            self._draw_board()
            self.after(20, self._run_solver_step)
        except StopIteration as e:
            # The generator is exhausted, meaning the solver has finished
            self.solver_running = False
            self._draw_board() # Final draw call to show the result
            if e.value: # The return value of the generator indicates success
                self.status_label.config(text="Solution Found!", fg="lightgreen")
            else:
                self.status_label.config(text="No solution exists.", fg="#FF5555")
            self.reset_zones_button.config(state=tk.NORMAL)

    def _update_attack_map(self):
        """Recalculates the entire attack map based on current piece placements."""
        self.attack_map = [[0 for _ in range(self.n)] for _ in range(self.n)]
        for r in range(self.n):
            for c in range(self.n):
                if self.board_state[r][c] == 1:
                    attacked_cells = self._get_attacked_cells(r, c)
                    for ar, ac in attacked_cells:
                        self.attack_map[ar][ac] += 1

    def _get_attacked_cells(self, r, c):
        """Dispatcher to get attack patterns for the current piece type."""
        if self.piece_type == "Queen":
            return self._get_queen_attacks(r, c)
        elif self.piece_type == "Superking":
            return self._get_superking_attacks(r, c)
        return []

    def _get_queen_attacks(self, r, c):
        """Returns a list of all cells attacked by a queen."""
        cells = []
        # Rook attacks
        for i in range(self.n):
            if i != c: cells.append((r, i))
            if i != r: cells.append((i, c))
        # Bishop attacks
        for i in range(1, self.n):
            for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                nr, nc = r + i * dr, c + i * dc
                if 0 <= nr < self.n and 0 <= nc < self.n:
                    cells.append((nr, nc))
        return cells

    def _get_superking_attacks(self, r, c):
        """Returns a list of all cells attacked by a superking (rook + king)."""
        cells = []
        # Rook attacks
        for i in range(self.n):
            if i != c: cells.append((r, i))
            if i != r: cells.append((i, c))
        # King attacks
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0: continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.n and 0 <= nc < self.n:
                    cells.append((nr, nc))
        # Use set to remove duplicates from overlapping rook/king moves
        return list(set(cells))

    def _is_safe(self, row, col):
        """
        Checks if a cell is a valid candidate for piece placement based on the
        current attack map and deduction map.
        """
        return self.attack_map[row][col] == 0 and self.deduction_map[row][col] != -1

    def _apply_deductions(self):
        """
        Dispatcher for all heuristic rules. It calls each rule function in
        sequence. Returns True if any rule made a deduction.
        """
        if self._apply_single_candidate_rule():
            return True
        
        if self._apply_locked_set_rule():
            return True

        if self._apply_walk_around_rule():
            return True
        
        return False

    def _apply_single_candidate_rule(self):
        """
        HEURISTIC 1: Finds and confirms a piece if it's the only possible
        candidate in a given row or column.
        """
        # Check rows for single candidates
        for r in range(self.n):
            candidate_cells = []
            for c in range(self.n):
                zone_idx = self.cell_to_zone_map[r][c]
                zone_has_piece = any(self.board_state[rz][cz] for rz, cz in self.zones[zone_idx])
                if not zone_has_piece and self._is_safe(r, c):
                    candidate_cells.append((r, c))
            
            if len(candidate_cells) == 1:
                pr, pc = candidate_cells[0]
                if self.board_state[pr][pc] == 0:
                    self.board_state[pr][pc] = 1
                    self.deduction_map[pr][pc] = 1
                    return True # A deduction was made

        # Check columns for single candidates
        for c in range(self.n):
            candidate_cells = []
            for r in range(self.n):
                zone_idx = self.cell_to_zone_map[r][c]
                zone_has_piece = any(self.board_state[rz][cz] for rz, cz in self.zones[zone_idx])
                if not zone_has_piece and self._is_safe(r, c):
                    candidate_cells.append((r, c))

            if len(candidate_cells) == 1:
                pr, pc = candidate_cells[0]
                if self.board_state[pr][pc] == 0:
                    self.board_state[pr][pc] = 1
                    self.deduction_map[pr][pc] = 1
                    return True # A deduction was made
        
        return False

    def _apply_locked_set_rule(self):
        """
        HEURISTIC 2: Finds "locked sets" (or "naked subsets"). If k zones
        have their candidates confined to exactly k rows or k columns, then no
        other zones can have their pieces in those rows/columns.
        """
        # We check for small sets first (k=2, 3, etc.) as they are more common.
        for k in range(2, self.n // 2 + 1):
            # Iterate through all combinations of k zones
            for zone_indices in combinations(range(self.n), k):
                # Rule applies only to zones that don't have a confirmed piece yet.
                if any(any(self.board_state[r][c] for r, c in self.zones[idx]) for idx in zone_indices):
                    continue

                # Collect all candidate cells from this group of k zones.
                all_candidates = []
                for idx in zone_indices:
                    all_candidates.extend([(r, c) for r, c in self.zones[idx] if self._is_safe(r, c)])

                if not all_candidates: continue
                
                # --- Check for sets locked in ROWS ---
                unique_rows = {r for r, c in all_candidates}
                if len(unique_rows) == k:
                    made_deduction = False
                    # Eliminate all candidates in these k rows that are NOT part of our k zones.
                    for r in unique_rows:
                        for c in range(self.n):
                            cell_zone_idx = self.cell_to_zone_map[r][c]
                            if cell_zone_idx not in zone_indices and self._is_safe(r, c):
                                self.deduction_map[r][c] = -1 # Mark as confirmed empty
                                made_deduction = True
                    if made_deduction: return True

                # --- Check for sets locked in COLUMNS ---
                unique_cols = {c for r, c in all_candidates}
                if len(unique_cols) == k:
                    made_deduction = False
                    # Eliminate all candidates in these k columns that are NOT part of our k zones.
                    for c in unique_cols:
                        for r in range(self.n):
                            cell_zone_idx = self.cell_to_zone_map[r][c]
                            if cell_zone_idx not in zone_indices and self._is_safe(r, c):
                                self.deduction_map[r][c] = -1 # Mark as confirmed empty
                                made_deduction = True
                    if made_deduction: return True
        
        return False

    def _apply_walk_around_rule(self):
        """
        HEURISTIC 3: The "Walk-Around" or mutual exclusion rule.
        If placing a hypothetical piece on a candidate cell outside a zone
        results in all candidate cells inside that zone being attacked, then
        the hypothetical cell cannot contain a piece.
        """
        # Iterate through each zone that does not yet have a confirmed piece.
        for zone_idx in range(self.n):
            if any(self.board_state[r][c] for r, c in self.zones[zone_idx]):
                continue

            # Get the set of all valid candidate cells within this target zone.
            zone_candidates = {
                (r, c) for r, c in self.zones[zone_idx]
                if self._is_safe(r, c)
            }
            if not zone_candidates:
                continue

            # Now, test every other valid candidate cell on the entire board.
            for test_r in range(self.n):
                for test_c in range(self.n):
                    # Skip cells inside our target zone and cells that are not candidates.
                    if self.cell_to_zone_map[test_r][test_c] == zone_idx:
                        continue
                    if not self._is_safe(test_r, test_c):
                        continue
                    
                    # Get all cells that would be attacked by this hypothetical piece.
                    attacked_by_test_piece = set(self._get_attacked_cells(test_r, test_c))

                    # If this hypothetical attack covers ALL candidates in our target zone...
                    if zone_candidates.issubset(attacked_by_test_piece):
                        # ...then placing a piece at (test_r, test_c) is impossible,
                        # as it would leave no valid placement for the target zone.
                        # Therefore, we can eliminate (test_r, test_c) as a candidate.
                        self.deduction_map[test_r][test_c] = -1
                        return True # A deduction was made.

        return False

    def _solver_entry_point(self):
        """
        The main generator that orchestrates the "deduce, then guess" process.
        """
        # --- 1. Deduction Phase ---
        # Loop applying heuristics until no more logical deductions can be made.
        while True:
            yield True # Yield True to signal a potential visual change
            if not self._apply_deductions():
                break # No more deductions found, proceed to backtracking
            self._update_attack_map()
        
        # --- 2. Backtracking (Guessing) Phase ---
        # If deductions didn't solve it, start backtracking.
        solution_found = yield from self._solver_backtrack()
        return solution_found


    def _solver_backtrack(self):
        """
        The recursive backtracking part of the solver. It makes an educated
        guess and explores the consequences, undoing the guess if it fails.
        """
        if not self.solver_running: return False

        # Base case: if N pieces are on the board, we have a solution.
        num_placed = sum(row.count(1) for row in self.board_state)
        if num_placed >= self.n:
            return True

        # Heuristic: Find the unassigned zone with the fewest candidate cells.
        # This is the "most constrained" zone, and tackling it first often
        # leads to faster solutions or failures.
        best_zone_idx = -1
        min_options = float('inf')
        candidate_cells = []

        for i in range(self.n):
            # Check if this zone already has a piece (either guessed or deduced)
            if any(self.board_state[r][c] for r, c in self.zones[i]):
                continue

            # Find all safe, non-deduced cells in this zone
            options = [ (r, c) for r, c in self.zones[i] if self._is_safe(r, c) ]
            if 0 < len(options) < min_options:
                min_options = len(options)
                best_zone_idx = i
                candidate_cells = options
        
        # If no valid moves are left in any zone, this path is a failure.
        if best_zone_idx == -1:
            return False

        # Try placing a piece in each candidate cell of the chosen zone.
        for r, c in candidate_cells:
            self.board_state[r][c] = 1
            self._update_attack_map()
            yield True # Yield for visualization

            # Recurse: try to solve the rest of the board with this guess.
            if (yield from self._solver_backtrack()):
                return True # Success! Propagate success up the call stack.
            
            # If we're here, the guess led to a dead end. Backtrack.
            if not self.solver_running: return False
            self.board_state[r][c] = 0 # Undo the guess
            self._update_attack_map()
            yield True # Yield for visualization

        return False # All candidates in this zone failed.

