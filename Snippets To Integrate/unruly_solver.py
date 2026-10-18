# puzzles/solver/unruly_solver.py
#
# Author: AlitheiaDeus & Gemini
# Date: 2025-08-28
#
# A hybrid solver for the "Unruly" binary puzzle. It first uses a robust
# set of deterministic logic rules. If logic alone cannot solve the puzzle,
# it seamlessly transitions to a recursive backtracking algorithm to find the
# solution via methodical trial-and-error.

import tkinter as tk
from tkinter import font, messagebox

class UnrulySolverApp(tk.Frame):
    """An interactive tool to define and solve Unruly puzzles."""

    # --- Constants for cell states and UI modes ---
    EMPTY = 0
    COLOR_A = 1 # Blue
    COLOR_B = 2 # Yellow

    MODE_COLOR = "color"
    MODE_EQUAL = "equal"
    MODE_OPPOSITE = "opposite"

    def __init__(self, master, show_main_menu_callback):
        super().__init__(master, bg="#2E2E2E")
        self.show_main_menu_callback = show_main_menu_callback
        self.solver_running = False
        self.show_setup_screen()

    def stop_game_loop(self):
        self.solver_running = False

    def _clear_container(self):
        for widget in self.winfo_children():
            widget.destroy()

    def show_setup_screen(self):
        self.stop_game_loop()
        self._clear_container()
        setup_frame = tk.Frame(self, bg="#2E2E2E")
        setup_frame.pack(expand=True)
        tk.Label(setup_frame, text="Unruly Puzzle Solver", font=("Helvetica", 24, "bold"), bg="#2E2E2E", fg="white").pack(pady=(20, 10))
        tk.Label(setup_frame, text="Define the grid size (must be an even number)", font=("Helvetica", 12), bg="#2E2E2E", fg="#CCCCCC").pack(pady=(0, 30))
        
        input_grid = tk.Frame(setup_frame, bg="#2E2E2E")
        input_grid.pack(pady=10)
        tk.Label(input_grid, text="Size (N x N):", font=("Helvetica", 12), bg="#2E2E2E", fg="white").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.size_entry = tk.Entry(input_grid, font=("Helvetica", 12), width=5, justify="center", bg="#3C3C3C", fg="white", insertbackground="white", relief="flat")
        self.size_entry.grid(row=0, column=1, padx=5, pady=5)
        self.size_entry.insert(0, "8")

        button_frame = tk.Frame(setup_frame, bg="#2E2E2E")
        button_frame.pack(pady=20)
        tk.Button(button_frame, text="Create Board", font=("Helvetica", 14), command=self.process_setup, bg="#4A4A4A", fg="white", relief="flat", padx=30, pady=10).pack(side="left", padx=10)
        tk.Button(button_frame, text="Back to Menu", font=("Helvetica", 14), command=self.show_main_menu_callback, bg="#4A4A4A", fg="white", relief="flat", padx=30, pady=10).pack(side="left", padx=10)

    def process_setup(self):
        try:
            n = int(self.size_entry.get())
            if n <= 1 or n % 2 != 0:
                messagebox.showerror("Invalid Size", "Grid size must be an even number greater than 1.")
                return
            if n > 14:
                messagebox.showinfo("Warning", "Backtracking on sizes > 14 can be very slow!")
            self.grid_size = n
            self.start_puzzle()
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid integer.")

    def start_puzzle(self):
        self.board = [[self.EMPTY for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        self.edge_constraints = {}
        self.show_board_ui()

    def show_board_ui(self):
        self._clear_container()
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        main_frame = tk.Frame(self, bg="#2E2E2E")
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)

        side_panel = tk.Frame(main_frame, bg="#2E2E2E", padx=10)
        side_panel.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        
        tk.Label(side_panel, text="Edit Mode", font=("Helvetica", 14, "bold"), bg="#2E2E2E", fg="white").pack(pady=(0, 10), anchor="w")
        self.edit_mode = tk.StringVar(value=self.MODE_COLOR)
        tk.Radiobutton(side_panel, text="Place Colors", variable=self.edit_mode, value=self.MODE_COLOR, bg="#2E2E2E", fg="white", selectcolor="#1E1E1E", activebackground="#2E2E2E", activeforeground="white", font=("Helvetica", 11)).pack(anchor="w")
        tk.Radiobutton(side_panel, text="Edges are Equal (=)", variable=self.edit_mode, value=self.MODE_EQUAL, bg="#2E2E2E", fg="white", selectcolor="#1E1E1E", activebackground="#2E2E2E", activeforeground="white", font=("Helvetica", 11)).pack(anchor="w")
        tk.Radiobutton(side_panel, text="Edges are Opposite (x)", variable=self.edit_mode, value=self.MODE_OPPOSITE, bg="#2E2E2E", fg="white", selectcolor="#1E1E1E", activebackground="#2E2E2E", activeforeground="white", font=("Helvetica", 11)).pack(anchor="w")

        tk.Label(side_panel, text="Rules", font=("Helvetica", 14, "bold"), bg="#2E2E2E", fg="white").pack(pady=(20, 10), anchor="w")
        self.unique_rows_cols = tk.BooleanVar(value=True)
        tk.Checkbutton(side_panel, text="Unique Rows & Columns", variable=self.unique_rows_cols, bg="#2E2E2E", fg="white", selectcolor="#1E1E1E", activebackground="#2E2E2E", activeforeground="white", font=("Helvetica", 11)).pack(anchor="w")

        action_frame = tk.Frame(side_panel, bg="#2E2E2E")
        action_frame.pack(pady=20, fill='x')
        self.solve_button = tk.Button(action_frame, text="Solve", command=self.solve_puzzle, font=("Helvetica", 12, "bold"), bg="#4CAF50", fg="white", relief="flat")
        self.solve_button.pack(pady=5, fill='x')
        self.reset_button = tk.Button(action_frame, text="Reset Board", command=self.start_puzzle, font=("Helvetica", 11), bg="#FF6B6B", fg="white", relief="flat")
        self.reset_button.pack(pady=5, fill='x')
        tk.Button(action_frame, text="New Size", command=self.show_setup_screen, font=("Helvetica", 11), bg="#3399FF", fg="white", relief="flat").pack(pady=5, fill='x')
        tk.Button(action_frame, text="Back to Menu", command=self.show_main_menu_callback, font=("Helvetica", 11), bg="#4A4A4A", fg="white", relief="flat").pack(pady=5, fill='x')
        self.status_label = tk.Label(side_panel, text="Define your puzzle.", font=("Helvetica", 10, "italic"), bg="#2E2E2E", fg="white", wraplength=150)
        self.status_label.pack(pady=10, fill='x')

        self.canvas = tk.Canvas(main_frame, bg="#1E1E1E", highlightthickness=0)
        self.canvas.grid(row=0, column=1, sticky="nsew")
        self.canvas.bind("<Configure>", lambda e: self.draw_board())
        self.canvas.bind("<Button-1>", self.handle_click)

    def draw_board(self):
        self.canvas.delete("all")
        canvas_w, canvas_h = self.canvas.winfo_width(), self.canvas.winfo_height()
        cell_dim = min(canvas_w / self.grid_size, canvas_h / self.grid_size)
        self.cell_size = cell_dim
        offset_x = (canvas_w - self.grid_size * self.cell_size) / 2
        offset_y = (canvas_h - self.grid_size * self.cell_size) / 2

        colors = {self.EMPTY: "#3C3C3C", self.COLOR_A: "#3399FF", self.COLOR_B: "#FFC107"}
        font_size = max(8, int(self.cell_size * 0.4))
        constraint_font = font.Font(family="Helvetica", size=font_size, weight="bold")

        for r in range(self.grid_size):
            for c in range(self.grid_size):
                x1, y1 = c * self.cell_size + offset_x, r * self.cell_size + offset_y
                x2, y2 = x1 + self.cell_size, y1 + self.cell_size
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=colors[self.board[r][c]], outline="#1E1E1E")

        for (r1, c1), (r2, c2) in self.edge_constraints:
            x_mid = ((c1 + c2) / 2 + 0.5) * self.cell_size + offset_x
            y_mid = ((r1 + r2) / 2 + 0.5) * self.cell_size + offset_y
            symbol = "=" if self.edge_constraints[((r1, c1), (r2, c2))] == self.MODE_EQUAL else "X"
            self.canvas.create_text(x_mid, y_mid, text=symbol, font=constraint_font, fill="#E74C3C")

    def handle_click(self, event):
        if self.solver_running: return
        canvas_w, canvas_h = self.canvas.winfo_width(), self.canvas.winfo_height()
        offset_x = (canvas_w - self.grid_size * self.cell_size) / 2
        offset_y = (canvas_h - self.grid_size * self.cell_size) / 2

        c = int((event.x - offset_x) // self.cell_size)
        r = int((event.y - offset_y) // self.cell_size)
        if not (0 <= c < self.grid_size and 0 <= r < self.grid_size): return
        
        mode = self.edit_mode.get()
        if mode == self.MODE_COLOR:
            self.board[r][c] = (self.board[r][c] + 1) % 3
        else:
            dx = (event.x - offset_x) - (c * self.cell_size)
            dy = (event.y - offset_y) - (r * self.cell_size)
            
            dist_to_top, dist_to_bottom = dy, self.cell_size - dy
            dist_to_left, dist_to_right = dx, self.cell_size - dx
            min_dist = min(dist_to_top, dist_to_bottom, dist_to_left, dist_to_right)

            if min_dist == dist_to_top and r > 0: self._toggle_edge_constraint(r, c, r-1, c, mode)
            elif min_dist == dist_to_bottom and r < self.grid_size - 1: self._toggle_edge_constraint(r, c, r+1, c, mode)
            elif min_dist == dist_to_left and c > 0: self._toggle_edge_constraint(r, c, r, c-1, mode)
            elif min_dist == dist_to_right and c < self.grid_size - 1: self._toggle_edge_constraint(r, c, r, c+1, mode)

        self.draw_board()

    def _toggle_edge_constraint(self, r1, c1, r2, c2, mode):
        key = tuple(sorted(((r1, c1), (r2, c2))))
        if key in self.edge_constraints and self.edge_constraints[key] == mode:
            del self.edge_constraints[key]
        else:
            self.edge_constraints[key] = mode

    def solve_puzzle(self):
        if self.solver_running:
            self.stop_game_loop()
            return
        
        self.solver_running = True
        self.solve_button.config(text="Stop")
        self.status_label.config(text="Applying logic...", fg="white")
        self.solver_generator = self._solver_orchestrator_gen()
        self.after(10, self._run_solver_step)

    def _run_solver_step(self):
        if not self.solver_running:
            self.solve_button.config(text="Solve")
            self.status_label.config(text="Solver stopped.")
            return
        try:
            final_result = next(self.solver_generator)
            if final_result is not None:
                 self._on_solver_finish(final_result)
                 return
            self.draw_board()
            self.after(1, self._run_solver_step)
        except StopIteration:
            is_solved = self._find_empty() is None
            self._on_solver_finish(is_solved)

    def _on_solver_finish(self, success):
        self.solver_running = False
        self.solve_button.config(text="Solve")
        if success:
            self.status_label.config(text="Solution Found!", fg="lightgreen")
        else:
            self.status_label.config(text="Could not find a valid solution.", fg="#FF5555")
        self.draw_board()

    #########################################################################
    ### --- HYBRID SOLVER LOGIC (DETERMINISTIC + BACKTRACKING) --- ############
    #########################################################################

    def _solver_orchestrator_gen(self):
        self.status_label.config(text="Applying logic...")
        while self.solver_running:
            made_change = self._apply_all_logic_rules()
            if made_change:
                yield
            else:
                break
        
        if self._find_empty() is None:
            yield self._validate_uniqueness()
            return

        self.status_label.config(text="Logic exhausted. Trying backtracking...")
        yield

        backtrack_solver = self._solve_with_backtracking_gen()
        final_success = False
        for success in backtrack_solver:
            if not self.solver_running:
                yield False
                return
            yield
            final_success = success
        
        yield final_success

    def _solve_with_backtracking_gen(self):
        find = self._find_empty()
        if not find:
            yield self._validate_uniqueness()
            return

        r, c = find
        for color in [self.COLOR_A, self.COLOR_B]:
            if self._is_valid(self.board, r, c, color):
                self.board[r][c] = color
                yield

                sub_solver = self._solve_with_backtracking_gen()
                is_solved = False
                for result in sub_solver:
                    yield
                    is_solved = result
                
                if is_solved:
                    yield True
                    return

                self.board[r][c] = self.EMPTY
                yield
        
        yield False

    def _apply_all_logic_rules(self):
        for i in range(self.grid_size):
            if self._apply_line_rules(i, -1): return True
            if self._apply_line_rules(-1, i): return True
        return False

    def _apply_line_rules(self, r, c):
        is_row = (c == -1)
        line = self.board[r] if is_row else [self.board[i][c] for i in range(self.grid_size)]
        
        if self.EMPTY not in line: return False

        if self._avoid_triples(r, c, line): return True
        if self._fill_sandwiches(r, c, line): return True
        if self._complete_by_count(r, c, line): return True
        if self._apply_hypothetical_completion(r, c, line): return True
        if self.unique_rows_cols.get() and self._apply_unique_pattern_rule(r, c, line): return True
        return False

    def _set_cell_and_propagate(self, r, c, color):
        if self.board[r][c] != self.EMPTY: return False
        if self._is_valid(self.board, r, c, color):
            self.board[r][c] = color
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.grid_size and 0 <= nc < self.grid_size:
                    key = tuple(sorted(((r, c), (nr, nc))))
                    if key in self.edge_constraints and self.board[nr][nc] == self.EMPTY:
                        constraint, other_color = self.edge_constraints[key], 3 - color
                        if constraint == self.MODE_EQUAL: self._set_cell_and_propagate(nr, nc, color)
                        elif constraint == self.MODE_OPPOSITE: self._set_cell_and_propagate(nr, nc, other_color)
            return True
        return False

    def _avoid_triples(self, r, c, line):
        made_change = False
        is_row, other_color = (c == -1), lambda col: 3 - col
        for i in range(self.grid_size - 1):
            if line[i] != self.EMPTY and line[i] == line[i+1]:
                if i > 0 and line[i-1] == self.EMPTY:
                    r_fill, c_fill = (r, i-1) if is_row else (i-1, c)
                    if self._set_cell_and_propagate(r_fill, c_fill, other_color(line[i])): made_change = True
                if i < self.grid_size - 2 and line[i+2] == self.EMPTY:
                    r_fill, c_fill = (r, i+2) if is_row else (i+2, c)
                    if self._set_cell_and_propagate(r_fill, c_fill, other_color(line[i])): made_change = True
        return made_change

    def _fill_sandwiches(self, r, c, line):
        made_change = False
        is_row, other_color = (c == -1), lambda col: 3 - col
        for i in range(self.grid_size - 2):
            if line[i] != self.EMPTY and line[i] == line[i+2] and line[i+1] == self.EMPTY:
                r_fill, c_fill = (r, i+1) if is_row else (i+1, c)
                if self._set_cell_and_propagate(r_fill, c_fill, other_color(line[i])): made_change = True
        return made_change

    def _complete_by_count(self, r, c, line):
        made_change, is_row, half_size = False, (c == -1), self.grid_size // 2
        count_a, count_b = line.count(self.COLOR_A), line.count(self.COLOR_B)
        fill_color = self.COLOR_B if count_a == half_size else (self.COLOR_A if count_b == half_size else None)
        if fill_color:
            for i in range(self.grid_size):
                if line[i] == self.EMPTY:
                    r_fill, c_fill = (r, i) if is_row else (i, c)
                    if self._set_cell_and_propagate(r_fill, c_fill, fill_color): made_change = True
        return made_change

    def _apply_hypothetical_completion(self, r, c, line):
        is_row, half_size = (c == -1), self.grid_size // 2
        empty_indices = [i for i, cell in enumerate(line) if cell == self.EMPTY]
        if len(empty_indices) <= 1: return False
        if line.count(self.COLOR_A) == half_size - 1:
            for idx in empty_indices:
                hypo_line = list(line); hypo_line[idx] = self.COLOR_A
                for i in empty_indices:
                    if i != idx: hypo_line[i] = self.COLOR_B
                if not self._is_line_valid(hypo_line):
                    r_fill, c_fill = (r, idx) if is_row else (idx, c)
                    if self._set_cell_and_propagate(r_fill, c_fill, self.COLOR_B): return True
        if line.count(self.COLOR_B) == half_size - 1:
            for idx in empty_indices:
                hypo_line = list(line); hypo_line[idx] = self.COLOR_B
                for i in empty_indices:
                    if i != idx: hypo_line[i] = self.COLOR_A
                if not self._is_line_valid(hypo_line):
                    r_fill, c_fill = (r, idx) if is_row else (idx, c)
                    if self._set_cell_and_propagate(r_fill, c_fill, self.COLOR_A): return True
        return False

    def _apply_unique_pattern_rule(self, r, c, line):
        is_row, empty_indices = (c == -1), [i for i, cell in enumerate(line) if cell == self.EMPTY]
        if len(empty_indices) != 2: return False
        
        idx1, idx2 = empty_indices
        completed_lines = set()
        if is_row: completed_lines = {tuple(b_row) for b_row in self.board if self.EMPTY not in b_row}
        else:
            for j in range(self.grid_size):
                col_tuple = tuple(self.board[i][j] for i in range(self.grid_size))
                if self.EMPTY not in col_tuple: completed_lines.add(col_tuple)
        
        if not completed_lines: return False
        
        # --- BUG FIX IS HERE ---
        # The original code had a tuple unpacking error on the r1,c1,r2,c2 assignment.
        # This corrected version unpacks the coordinates for each cell properly.
        if is_row:
            (r1, c1), (r2, c2) = (r, idx1), (r, idx2)
        else: # is column
            (r1, c1), (r2, c2) = (idx1, c), (idx2, c)
        
        hypo1 = list(line); hypo1[idx1], hypo1[idx2] = self.COLOR_A, self.COLOR_B
        if tuple(hypo1) in completed_lines:
            if self._is_valid(self.board, r1, c1, self.COLOR_B) and self._is_valid(self.board, r2, c2, self.COLOR_A):
                self._set_cell_and_propagate(r1, c1, self.COLOR_B)
                self._set_cell_and_propagate(r2, c2, self.COLOR_A)
                return True
        
        hypo2 = list(line); hypo2[idx1], hypo2[idx2] = self.COLOR_B, self.COLOR_A
        if tuple(hypo2) in completed_lines:
            if self._is_valid(self.board, r1, c1, self.COLOR_A) and self._is_valid(self.board, r2, c2, self.COLOR_B):
                self._set_cell_and_propagate(r1, c1, self.COLOR_A)
                self._set_cell_and_propagate(r2, c2, self.COLOR_B)
                return True
        return False

    def _find_empty(self):
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                if self.board[r][c] == self.EMPTY: return r, c
        return None

    def _validate_uniqueness(self):
        if not self.unique_rows_cols.get(): return True
        rows = {tuple(row) for row in self.board}
        if len(rows) != self.grid_size: return False
        cols = {tuple(self.board[r][c] for r in range(self.grid_size)) for c in range(self.grid_size)}
        if len(cols) != self.grid_size: return False
        return True

    def _is_line_valid(self, line):
        for i in range(len(line) - 2):
            if line[i] != self.EMPTY and line[i] == line[i+1] == line[i+2]: return False
        return True

    def _is_valid(self, board, r, c, color):
        temp_board = [row[:] for row in board]; temp_board[r][c] = color
        row, col = temp_board[r], [temp_board[i][c] for i in range(self.grid_size)]
        if not self._is_line_valid(row) or not self._is_line_valid(col): return False
        half_size = self.grid_size // 2
        if row.count(color) > half_size or col.count(color) > half_size: return False
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.grid_size and 0 <= nc < self.grid_size:
                key = tuple(sorted(((r, c), (nr, nc))))
                if key in self.edge_constraints:
                    neighbor_color = temp_board[nr][nc]
                    if neighbor_color != self.EMPTY:
                        constraint = self.edge_constraints[key]
                        if constraint == self.MODE_EQUAL and color != neighbor_color: return False
                        if constraint == self.MODE_OPPOSITE and color == neighbor_color: return False
        return True