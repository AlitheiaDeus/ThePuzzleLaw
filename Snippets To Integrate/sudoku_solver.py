# puzzles/solver/sudoku_solver.py
#
# Author: AlitheiaDeus & Gemini
# Date: 2025-08-28
#
# A highly flexible Sudoku solver that supports custom grid sizes and employs
# a hybrid solving strategy. It first uses logical deduction (Naked/Hidden Singles)
# and only resorts to backtracking when logic alone cannot solve the puzzle.

import tkinter as tk
from tkinter import font, messagebox
import math

class SudokuSolverApp(tk.Frame):
    """An interactive and customizable Sudoku solver."""
    def __init__(self, master, show_main_menu_callback):
        super().__init__(master, bg="#2E2E2E")
        self.show_main_menu_callback = show_main_menu_callback
        self.solver_running = False
        self.show_setup_screen()

    def stop_game_loop(self):
        """Stops any ongoing animations or loops."""
        self.solver_running = False

    def _clear_container(self):
        """Removes all widgets from the frame."""
        for widget in self.winfo_children():
            widget.destroy()

    def show_setup_screen(self):
        """Displays the screen for setting up custom grid dimensions."""
        self.stop_game_loop()
        self._clear_container()

        setup_frame = tk.Frame(self, bg="#2E2E2E")
        setup_frame.pack(expand=True)

        tk.Label(setup_frame, text="Custom Sudoku Solver", font=("Helvetica", 24, "bold"), bg="#2E2E2E", fg="white").pack(pady=(20, 10))
        tk.Label(setup_frame, text="Define the grid and sub-grid (box) dimensions", font=("Helvetica", 12), bg="#2E2E2E", fg="#CCCCCC").pack(pady=(0, 30))

        # --- Input Grid ---
        input_grid = tk.Frame(setup_frame, bg="#2E2E2E")
        input_grid.pack(pady=10)

        # Grid Dimensions
        tk.Label(input_grid, text="Grid Dimension:", font=("Helvetica", 12), bg="#2E2E2E", fg="white").grid(row=0, column=0, columnspan=2, padx=5, pady=5)
        self.grid_dim_entry = tk.Entry(input_grid, font=("Helvetica", 12), width=5, justify="center", bg="#3C3C3C", fg="white", insertbackground="white", relief="flat")
        self.grid_dim_entry.grid(row=0, column=2, columnspan=2, padx=5, pady=5)
        self.grid_dim_entry.insert(0, "9")

        # Box Dimensions
        tk.Label(input_grid, text="Box Width:", font=("Helvetica", 12), bg="#2E2E2E", fg="white").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.box_w_entry = tk.Entry(input_grid, font=("Helvetica", 12), width=5, justify="center", bg="#3C3C3C", fg="white", insertbackground="white", relief="flat")
        self.box_w_entry.grid(row=1, column=1, padx=5, pady=5)
        self.box_w_entry.insert(0, "3")

        tk.Label(input_grid, text="Box Height:", font=("Helvetica", 12), bg="#2E2E2E", fg="white").grid(row=1, column=2, padx=5, pady=5, sticky="e")
        self.box_h_entry = tk.Entry(input_grid, font=("Helvetica", 12), width=5, justify="center", bg="#3C3C3C", fg="white", insertbackground="white", relief="flat")
        self.box_h_entry.grid(row=1, column=3, padx=5, pady=5)
        self.box_h_entry.insert(0, "3")

        # --- Buttons ---
        button_frame = tk.Frame(setup_frame, bg="#2E2E2E")
        button_frame.pack(pady=20)
        tk.Button(button_frame, text="Start", font=("Helvetica", 14), command=self.process_setup, bg="#4A4A4A", fg="white", relief="flat", padx=30, pady=10).pack(side="left", padx=10)
        tk.Button(button_frame, text="Back to Menu", font=("Helvetica", 14), command=self.show_main_menu_callback, bg="#4A4A4A", fg="white", relief="flat", padx=30, pady=10).pack(side="left", padx=10)

    def process_setup(self):
        """Validates dimensions and initializes the puzzle."""
        try:
            self.box_w = int(self.box_w_entry.get())
            self.box_h = int(self.box_h_entry.get())
            self.grid_dim = int(self.grid_dim_entry.get())

            if self.grid_dim != self.box_w * self.box_h:
                 messagebox.showerror("Invalid Dimensions", f"Grid dimension ({self.grid_dim}) must equal Box Width x Box Height ({self.box_w}x{self.box_h}={self.box_w*self.box_h}).")
                 return
            if self.grid_dim <= 1 or self.grid_dim > 16: # Cap size for usability
                 messagebox.showerror("Invalid Dimensions", "Grid dimension must be between 2 and 16.")
                 return

            self.symbols = [str(i) for i in range(1, self.grid_dim + 1)]
            self.start_puzzle()
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid integers for all dimensions.")

    def start_puzzle(self):
        """Initializes the board for user input."""
        self.board = [[0 for _ in range(self.grid_dim)] for _ in range(self.grid_dim)]
        self.show_board_ui()

    def show_board_ui(self):
        """Displays the interactive Sudoku grid, now with high-contrast sub-grid borders."""
        self._clear_container()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        main_frame = tk.Frame(self, bg="#2E2E2E")
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

        board_frame = tk.Frame(main_frame, bg="#555555") # Lighter background for better contrast
        board_frame.grid(row=0, column=0, pady=(0, 20))

        self.cells = [[None for _ in range(self.grid_dim)] for _ in range(self.grid_dim)]
        validate_cmd = self.register(self._validate_input)
        font_size = max(8, 30 - self.grid_dim)

        for r in range(self.grid_dim):
            for c in range(self.grid_dim):
                padx = (2, 0) if c % self.box_w == 0 else (1, 0)
                pady = (2, 0) if r % self.box_h == 0 else (1, 0)

                entry = tk.Entry(
                    board_frame,
                    font=("Helvetica", font_size, "bold"),
                    justify="center",
                    bg="#3C3C3C", fg="white",
                    insertbackground="white", relief="flat",
                    width=2,
                    validate="key",
                    validatecommand=(validate_cmd, '%P')
                )
                entry.grid(row=r, column=c, padx=padx, pady=pady, sticky="nsew")
                self.cells[r][c] = entry

        # Control Frame
        control_frame = tk.Frame(main_frame, bg="#2E2E2E")
        control_frame.grid(row=1, column=0, sticky="ew")
        control_frame.grid_columnconfigure(0, weight=1)
        button_group = tk.Frame(control_frame, bg="#2E2E2E")
        button_group.pack()

        self.solve_button = tk.Button(button_group, text="Solve", command=self.solve_puzzle, font=("Helvetica", 12, "bold"), bg="#4CAF50", fg="white", relief="flat", padx=15, pady=5)
        self.solve_button.pack(side=tk.LEFT, padx=10)
        self.clear_button = tk.Button(button_group, text="Clear Board", command=self.clear_board, font=("Helvetica", 12), bg="#FF6B6B", fg="white", relief="flat", padx=15, pady=5)
        self.clear_button.pack(side=tk.LEFT, padx=10)
        tk.Button(button_group, text="New Puzzle", command=self.show_setup_screen, font=("Helvetica", 12), bg="#3399FF", fg="white", relief="flat", padx=15, pady=5).pack(side=tk.LEFT, padx=10)
        tk.Button(button_group, text="Back to Menu", command=self.show_main_menu_callback, font=("Helvetica", 12), bg="#4A4A4A", fg="white", relief="flat", padx=15, pady=5).pack(side=tk.LEFT, padx=10)

        self.status_label = tk.Label(main_frame, text="Fill the grid and press 'Solve'.", font=("Helvetica", 12, "italic"), bg="#2E2E2E", fg="white")
        self.status_label.grid(row=2, column=0, pady=(20, 0))

    def _validate_input(self, value):
        """Ensures input is a valid symbol for the current grid size."""
        if value == "": return True
        return value in self.symbols

    def clear_board(self):
        if self.solver_running: return
        self.stop_game_loop()
        for r in range(self.grid_dim):
            for c in range(self.grid_dim):
                self.cells[r][c].config(state=tk.NORMAL, fg="white")
                self.cells[r][c].delete(0, tk.END)
        self.status_label.config(text="Board cleared.", fg="white")
        self.solve_button.config(state=tk.NORMAL)
        self.clear_button.config(text="Clear Board")

    def solve_puzzle(self):
        """Initiates the new hybrid solver."""
        if self.solver_running:
            self.stop_game_loop()
            return

        # Read board from UI
        try:
            for r in range(self.grid_dim):
                for c in range(self.grid_dim):
                    val = self.cells[r][c].get()
                    self.board[r][c] = int(val) if val else 0
        except ValueError:
            messagebox.showerror("Invalid Input", "Invalid number in grid.")
            return

        # Validate initial state
        if not self._is_board_state_valid(self.board):
            messagebox.showerror("Invalid Puzzle", "Initial state is invalid (duplicates found).")
            return

        # Lock initial numbers
        for r in range(self.grid_dim):
            for c in range(self.grid_dim):
                if self.board[r][c] != 0:
                    self.cells[r][c].config(state='readonly', fg="#66b3ff")

        self.solver_running = True
        self.solve_button.config(text="Stop")
        self.clear_button.config(state=tk.DISABLED)
        self.status_label.config(text="Solving...", fg="yellow")

        self.solver_generator = self._hybrid_solver()
        self.after(10, self._run_solver_step)

    def _run_solver_step(self):
        if not self.solver_running:
            self.solve_button.config(text="Solve")
            self.clear_button.config(state=tk.NORMAL)
            self.status_label.config(text="Solver stopped.", fg="white")
            return
        try:
            next(self.solver_generator)
            self.after(1, self._run_solver_step)
        except StopIteration as e:
            self._on_solver_finish(e.value)

    def _on_solver_finish(self, success):
        self.solver_running = False
        self.status_label.config(text="Solution Found!" if success else "Unsolvable.",
                                 fg="lightgreen" if success else "#FF5555")
        self.solve_button.config(state=tk.DISABLED)
        self.clear_button.config(state=tk.NORMAL, text="Reset")

    def _hybrid_solver(self):
        """Generator that orchestrates the logical and backtracking solvers."""
        # 1. Create candidate map (pencil marks)
        candidates = self._get_initial_candidates(self.board)
        if candidates is None: # Inconsistent board
            yield
            return False

        # 2. Main logical loop
        stalled = False
        while not stalled:
            stalled = True
            solved_cells_before = sum(row.count(0) for row in self.board)

            # Strategy 1: Naked Singles
            for r in range(self.grid_dim):
                for c in range(self.grid_dim):
                    if self.board[r][c] == 0 and len(candidates[r][c]) == 1:
                        num = candidates[r][c].pop()
                        self._place_number(self.board, candidates, r, c, num)
                        stalled = False
                        yield

            # Strategy 2: Hidden Singles
            if stalled:
                for unit in self._get_all_units():
                    for num in range(1, self.grid_dim + 1):
                        places = [ (r,c) for r,c in unit if self.board[r][c] == 0 and num in candidates[r][c] ]
                        if len(places) == 1:
                            r, c = places[0]
                            self._place_number(self.board, candidates, r, c, num)
                            stalled = False
                            yield
            
            if not self._is_board_state_valid(self.board, candidates):
                yield
                return False

            if solved_cells_before == sum(row.count(0) for row in self.board) and stalled:
                break # No progress was made

        # 3. If not solved, fall back to backtracking
        if self._find_empty(self.board):
            self.status_label.config(text="Logic stalled, backtracking...")
            yield
            backtrack_gen = self._backtrack_solver(self.board, candidates)
            return (yield from backtrack_gen)

        return True

    def _backtrack_solver(self, board, candidates):
        """Recursive backtracking part of the solver."""
        if not self.solver_running: return False

        find = self._find_empty_with_fewest_candidates(board, candidates)
        if not find:
            return True

        r, c = find
        # Try numbers from the candidate list
        sorted_candidates = sorted(list(candidates[r][c]))
        for num in sorted_candidates:
            if self._is_safe(board, num, (r, c)):
                board[r][c] = num
                self.cells[r][c].delete(0, tk.END)
                self.cells[r][c].insert(0, str(num))
                yield

                # Recurse
                if (yield from self._backtrack_solver(board, candidates)):
                    return True

                # Backtrack
                if not self.solver_running: return False
                board[r][c] = 0
                self.cells[r][c].delete(0, tk.END)
                yield
        return False

    # --- Helper and Logic Methods ---

    def _place_number(self, board, candidates, r, c, num):
        """Places a number and updates the candidate lists of affected cells."""
        board[r][c] = num
        self.cells[r][c].delete(0, tk.END)
        self.cells[r][c].insert(0, str(num))
        candidates[r][c] = set() # This cell is solved

        # Remove from peers
        for pr, pc in self._get_peers(r, c):
            if num in candidates[pr][pc]:
                candidates[pr][pc].remove(num)

    def _get_initial_candidates(self, board):
        """Generates the initial candidate map for all empty cells."""
        candidates = [[set() for _ in range(self.grid_dim)] for _ in range(self.grid_dim)]
        for r in range(self.grid_dim):
            for c in range(self.grid_dim):
                if board[r][c] == 0:
                    possible = set(range(1, self.grid_dim + 1))
                    for pr, pc in self._get_peers(r, c):
                        if board[pr][pc] != 0:
                            possible.discard(board[pr][pc])
                    candidates[r][c] = possible
        return candidates

    def _is_board_state_valid(self, board, candidates=None):
        """Checks for obvious contradictions in the board or candidates."""
        for unit in self._get_all_units():
            nums = [board[r][c] for r, c in unit if board[r][c] != 0]
            if len(nums) != len(set(nums)):
                return False # Duplicate found
        if candidates:
            for r in range(self.grid_dim):
                for c in range(self.grid_dim):
                    if board[r][c] == 0 and not candidates[r][c]:
                        return False # Empty cell with no candidates
        return True

    def _get_peers(self, r, c):
        """Returns a set of all peer cells for a given cell."""
        peers = set()
        # Row and Column
        for i in range(self.grid_dim):
            if i != c: peers.add((r, i))
            if i != r: peers.add((i, c))
        # Box
        start_row = r - r % self.box_h
        start_col = c - c % self.box_w
        for i in range(self.box_h):
            for j in range(self.box_w):
                if (start_row + i, start_col + j) != (r, c):
                    peers.add((start_row + i, start_col + j))
        return peers
    
    def _get_all_units(self):
        """Generator for all rows, columns, and boxes."""
        # Rows
        for r in range(self.grid_dim):
            yield [(r, c) for c in range(self.grid_dim)]
        # Columns
        for c in range(self.grid_dim):
            yield [(r, c) for r in range(self.grid_dim)]
        # Boxes
        for br in range(0, self.grid_dim, self.box_h):
            for bc in range(0, self.grid_dim, self.box_w):
                yield [(br+r, bc+c) for r in range(self.box_h) for c in range(self.box_w)]

    def _find_empty(self, board):
        for r in range(self.grid_dim):
            for c in range(self.grid_dim):
                if board[r][c] == 0:
                    return (r, c)
        return None

    def _find_empty_with_fewest_candidates(self, board, candidates):
        """Finds an empty cell with the minimum number of candidates."""
        min_len = self.grid_dim + 1
        best_pos = None
        for r in range(self.grid_dim):
            for c in range(self.grid_dim):
                if board[r][c] == 0:
                    num_candidates = len(candidates[r][c])
                    if num_candidates < min_len:
                        min_len = num_candidates
                        best_pos = (r, c)
        return best_pos

    def _is_safe(self, board, num, pos):
        """Checks if placing a number is valid (used by backtrack)."""
        r, c = pos
        # Check row, column, and box
        for pr, pc in self._get_peers(r, c):
            if board[pr][pc] == num:
                return False
        return True

