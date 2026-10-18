# puzzles/solver/flow_solver.py
#
# Author: AlitheiaDeus & Gemini
# Date: 2025-08-28
#
# A hybrid solver for "Flow" puzzles. It uses a constraint-based "gates"
# method for forced moves and switches to a recursive backtracking algorithm
# to explore choices. Includes a flood-fill check to prevent region splitting.

import tkinter as tk
from tkinter import font, messagebox
from collections import deque

class FlowSolverApp(tk.Frame):
    """An interactive tool to define and solve Flow puzzles with edge-based walls."""

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
        tk.Label(setup_frame, text="Flow Puzzle Solver", font=("Helvetica", 24, "bold"), bg="#2E2E2E", fg="white").pack(pady=(20, 10))
        tk.Label(setup_frame, text="Define the grid dimensions", font=("Helvetica", 12), bg="#2E2E2E", fg="#CCCCCC").pack(pady=(0, 30))
        input_grid = tk.Frame(setup_frame, bg="#2E2E2E")
        input_grid.pack(pady=10)
        tk.Label(input_grid, text="Width:", font=("Helvetica", 12), bg="#2E2E2E", fg="white").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.width_entry = tk.Entry(input_grid, font=("Helvetica", 12), width=5, justify="center", bg="#3C3C3C", fg="white", insertbackground="white", relief="flat")
        self.width_entry.grid(row=0, column=1, padx=5, pady=5)
        self.width_entry.insert(0, "7")
        tk.Label(input_grid, text="Height:", font=("Helvetica", 12), bg="#2E2E2E", fg="white").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.height_entry = tk.Entry(input_grid, font=("Helvetica", 12), width=5, justify="center", bg="#3C3C3C", fg="white", insertbackground="white", relief="flat")
        self.height_entry.grid(row=1, column=1, padx=5, pady=5)
        self.height_entry.insert(0, "7")
        button_frame = tk.Frame(setup_frame, bg="#2E2E2E")
        button_frame.pack(pady=20)
        tk.Button(button_frame, text="Create Board", font=("Helvetica", 14), command=self.process_setup, bg="#4A4A4A", fg="white", relief="flat", padx=30, pady=10).pack(side="left", padx=10)
        tk.Button(button_frame, text="Back to Menu", font=("Helvetica", 14), command=self.show_main_menu_callback, bg="#4A4A4A", fg="white", relief="flat", padx=30, pady=10).pack(side="left", padx=10)

    def process_setup(self):
        try:
            self.grid_w = int(self.width_entry.get())
            self.grid_h = int(self.height_entry.get())
            if self.grid_w <= 1 or self.grid_h <= 1 or self.grid_w > 20 or self.grid_h > 20:
                messagebox.showerror("Invalid Dimensions", "Dimensions must be between 2 and 20.")
                return
            self.start_puzzle()
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid integers for dimensions.")

    def start_puzzle(self):
        self.walls = [[{'N': False, 'E': False, 'S': False, 'W': False} for _ in range(self.grid_w)] for _ in range(self.grid_h)]
        self.checkpoints = {}
        self.next_checkpoint_num = 1
        self.solution_path = []
        self.show_board_ui()

    def show_board_ui(self):
        self._clear_container()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        main_frame = tk.Frame(self, bg="#2E2E2E")
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)

        side_panel = tk.Frame(main_frame, bg="#2E2E2E", padx=10)
        side_panel.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        
        tk.Label(side_panel, text="Controls", font=("Helvetica", 14, "bold"), bg="#2E2E2E", fg="white").pack(pady=(0, 10), anchor="w")
        tk.Label(side_panel, text="Left-Click: Place Wall/CP\nRight-Click: Erase Wall/CP", justify="left", font=("Helvetica", 10), bg="#2E2E2E", fg="#CCCCCC").pack(pady=(0, 20), anchor="w")
        
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
        self.canvas.bind("<Button-1>", self.handle_left_click)
        self.canvas.bind("<B1-Motion>", self.handle_left_click)
        self.canvas.bind("<Button-3>", self.handle_right_click)
        self.canvas.bind("<B3-Motion>", self.handle_right_click)


    def draw_board(self):
        self.canvas.delete("all")
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        
        cell_dim = min(canvas_w / self.grid_w, canvas_h / self.grid_h)
        self.cell_w = self.cell_h = cell_dim
        
        offset_x = (canvas_w - self.grid_w * self.cell_w) / 2
        offset_y = (canvas_h - self.grid_h * self.cell_h) / 2

        font_size = max(8, int(self.cell_w * 0.5))
        cp_font = font.Font(family="Helvetica", size=font_size, weight="bold")
        wall_color, wall_width = "#AAAAFF", 3

        for r in range(self.grid_h):
            for c in range(self.grid_w):
                x1, y1 = c * self.cell_w + offset_x, r * self.cell_h + offset_y
                x2, y2 = x1 + self.cell_w, y1 + self.cell_h
                self.canvas.create_rectangle(x1, y1, x2, y2, fill="#3C3C3C", outline="#1E1E1E")

        if self.solution_path:
            for i in range(len(self.solution_path) - 1):
                r1, c1 = self.solution_path[i]
                r2, c2 = self.solution_path[i+1]
                x1, y1 = c1 * self.cell_w + self.cell_w / 2 + offset_x, r1 * self.cell_h + self.cell_h / 2 + offset_y
                x2, y2 = c2 * self.cell_w + self.cell_w / 2 + offset_x, r2 * self.cell_h + self.cell_h / 2 + offset_y
                self.canvas.create_line(x1, y1, x2, y2, fill="#4CAF50", width=max(2, font_size*0.5), capstyle=tk.ROUND)

        for r in range(self.grid_h):
            for c in range(self.grid_w):
                x1, y1 = c * self.cell_w + offset_x, r * self.cell_h + offset_y
                x2, y2 = x1 + self.cell_w, y1 + self.cell_h
                if self.walls[r][c]['N']: self.canvas.create_line(x1, y1, x2, y1, fill=wall_color, width=wall_width)
                if self.walls[r][c]['E']: self.canvas.create_line(x2, y1, x2, y2, fill=wall_color, width=wall_width)
                if self.walls[r][c]['S']: self.canvas.create_line(x1, y2, x2, y2, fill=wall_color, width=wall_width)
                if self.walls[r][c]['W']: self.canvas.create_line(x1, y1, x1, y2, fill=wall_color, width=wall_width)

        for num, (r, c) in self.checkpoints.items():
            x1, y1 = c * self.cell_w + offset_x, r * self.cell_h + offset_y
            padding = self.cell_w * 0.15 # Make checkpoints smaller
            self.canvas.create_oval(x1 + padding, y1 + padding, x1 + self.cell_w - padding, y1 + self.cell_h - padding, fill="#3399FF", outline="")
            self.canvas.create_text(x1 + self.cell_w/2, y1 + self.cell_h/2, text=str(num), font=cp_font, fill="white")

    def _get_click_location(self, event):
        canvas_w, canvas_h = self.canvas.winfo_width(), self.canvas.winfo_height()
        offset_x = (canvas_w - self.grid_w * self.cell_w) / 2
        offset_y = (canvas_h - self.grid_h * self.cell_h) / 2

        c = int((event.x - offset_x) // self.cell_w)
        r = int((event.y - offset_y) // self.cell_h)
        
        if not (0 <= c < self.grid_w and 0 <= r < self.grid_h):
            return None, None, None

        dx = (event.x - offset_x) - (c * self.cell_w)
        dy = (event.y - offset_y) - (r * self.cell_h)
        
        edge_threshold = 0.25
        on_edge = (dy < self.cell_h * edge_threshold or dy > self.cell_h * (1 - edge_threshold) or
                   dx < self.cell_w * edge_threshold or dx > self.cell_w * (1 - edge_threshold))
        
        return r, c, on_edge

    def handle_left_click(self, event):
        if self.solver_running: return
        r, c, on_edge = self._get_click_location(event)
        if r is None: return

        if on_edge:
            self._handle_wall_placement(event, r, c, True)
        else:
            if (r, c) not in self.checkpoints.values():
                self.checkpoints[self.next_checkpoint_num] = (r, c)
                self.next_checkpoint_num += 1
        self.draw_board()
        
    def handle_right_click(self, event):
        if self.solver_running: return
        r, c, on_edge = self._get_click_location(event)
        if r is None: return

        if on_edge:
            self._handle_wall_placement(event, r, c, False)
        else:
            if (r, c) in self.checkpoints.values():
                self._erase_checkpoint(r, c)
        self.draw_board()

    def _handle_wall_placement(self, event, r, c, state):
        canvas_w, canvas_h = self.canvas.winfo_width(), self.canvas.winfo_height()
        offset_x = (canvas_w - self.grid_w * self.cell_w) / 2
        offset_y = (canvas_h - self.grid_h * self.cell_h) / 2
        dx = (event.x - offset_x) - (c * self.cell_w)
        dy = (event.y - offset_y) - (r * self.cell_h)
        
        dist_to_top, dist_to_bottom = dy, self.cell_h - dy
        dist_to_left, dist_to_right = dx, self.cell_w - dx
        min_dist = min(dist_to_top, dist_to_bottom, dist_to_left, dist_to_right)

        if min_dist == dist_to_top: self._toggle_wall(r, c, 'N', state)
        elif min_dist == dist_to_bottom: self._toggle_wall(r, c, 'S', state)
        elif min_dist == dist_to_left: self._toggle_wall(r, c, 'W', state)
        else: self._toggle_wall(r, c, 'E', state)

    def _toggle_wall(self, r, c, direction, state):
        self.walls[r][c][direction] = state
        if direction == 'N' and r > 0: self.walls[r-1][c]['S'] = state
        if direction == 'S' and r < self.grid_h - 1: self.walls[r+1][c]['N'] = state
        if direction == 'W' and c > 0: self.walls[r][c-1]['E'] = state
        if direction == 'E' and c < self.grid_w - 1: self.walls[r][c+1]['W'] = state

    def _erase_checkpoint(self, r, c):
        num_to_remove = [k for k, v in self.checkpoints.items() if v == (r, c)][0]
        del self.checkpoints[num_to_remove]
        new_checkpoints = {}
        sorted_keys = sorted(self.checkpoints.keys())
        for i, key in enumerate(sorted_keys):
            new_checkpoints[i + 1] = self.checkpoints[key]
        self.checkpoints = new_checkpoints
        self.next_checkpoint_num = len(self.checkpoints) + 1

    def solve_puzzle(self):
        if self.solver_running:
            self.stop_game_loop()
            return
        if 1 not in self.checkpoints:
            messagebox.showerror("Invalid Puzzle", "Puzzle must have a '1' checkpoint.")
            return

        self.solver_running = True
        self.solve_button.config(text="Stop")
        self.status_label.config(text="Solving...")
        
        self.total_cells = self.grid_w * self.grid_h
        self.solution_path = []

        self.solver_generator = self._solve_recursive_gen_wrapper()
        self.after(10, self._run_solver_step)

    def _run_solver_step(self):
        if not self.solver_running:
            self.solve_button.config(text="Solve")
            self.status_label.config(text="Solver stopped.")
            return
        try:
            for _ in range(20): # Speed up animation
                if not self.solver_running: break
                next(self.solver_generator)
            self.draw_board()
            self.after(1, self._run_solver_step)
        except StopIteration as e:
            self._on_solver_finish(e.value)

    def _on_solver_finish(self, success):
        self.solver_running = False
        self.solve_button.config(text="Solve")
        self.status_label.config(text="Solution Found!" if success else "No solution exists.", fg="lightgreen" if success else "#FF5555")
        self.draw_board()

    def _get_open_gates(self, r, c, path):
        gates = []
        directions = [('N', -1, 0), ('E', 0, 1), ('S', 1, 0), ('W', 0, -1)]
        for D, dr, dc in directions:
            if not self.walls[r][c][D]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.grid_h and 0 <= nc < self.grid_w and (nr, nc) not in path:
                    gates.append((nr, nc))
        return gates

    def _is_region_valid(self, path):
        unvisited = []
        path_set = set(path)
        for r in range(self.grid_h):
            for c in range(self.grid_w):
                if (r, c) not in path_set:
                    unvisited.append((r,c))
        
        if not unvisited: return True

        q = deque([unvisited[0]])
        reachable = {unvisited[0]}
        while q:
            r, c = q.popleft()
            for nr, nc in self._get_open_gates(r, c, path):
                if (nr, nc) in unvisited and (nr, nc) not in reachable:
                    reachable.add((nr, nc))
                    q.append((nr, nc))
        
        return len(reachable) == len(unvisited)

    def _solve_recursive_gen_wrapper(self):
        initial_path = [self.checkpoints[1]]
        result = yield from self._solve_recursive(initial_path, 2)
        return result

    def _solve_recursive(self, path, target_cp):
        """
        A recursive backtracking solver that finds a path visiting all checkpoints
        in order, filling the entire grid, and ending on the last checkpoint.
        """
        if not self.solver_running:
            return False

        # If we have hit all checkpoints, the only way to succeed is if the grid is also full.
        # This is the primary success condition, checked when the last CP is reached.
        if target_cp > len(self.checkpoints):
            if len(path) == self.total_cells:
                self.solution_path = list(path)
                return True
            else:
                # Reached all CPs but grid isn't full, so this is a dead end.
                return False

        # If the grid is full but we haven't hit all checkpoints, it's a dead end.
        if len(path) == self.total_cells:
            return False

        current_pos = path[-1]
        open_gates = self._get_open_gates(current_pos[0], current_pos[1], path)

        for next_pos in open_gates:
            path.append(next_pos)
            
            if not self._is_region_valid(path):
                path.pop()
                continue

            self.solution_path = list(path)
            yield

            new_target_cp = target_cp
            # Check if the next position is the checkpoint we're looking for
            if target_cp <= len(self.checkpoints) and next_pos == self.checkpoints[target_cp]:
                new_target_cp += 1
            # Check if we landed on any other checkpoint out of order
            elif next_pos in self.checkpoints.values():
                path.pop()
                continue

            # Recurse with the new state
            result = yield from self._solve_recursive(path, new_target_cp)
            if result:
                return True

            # Backtrack
            path.pop()
            self.solution_path = list(path)
            yield

        return False
