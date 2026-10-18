# puzzles/flip_solver.py

import tkinter as tk
from tkinter import font, messagebox

# --- Conditional Import for Numpy ---
# The linear algebra is much cleaner and faster with numpy, but this
# module will fall back to a pure Python implementation if it's not found.
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False
    print("Warning: Numpy not found. Flip solver will use a slower list-based implementation.")


class FlipSolverApp(tk.Frame):
    """An interactive tool to solve the 'Flip' (Lights Out) puzzle."""
    def __init__(self, master, show_main_menu_callback):
        super().__init__(master, bg="#2E2E2E")
        self.show_main_menu_callback = show_main_menu_callback
        self.show_start_menu()

    def _clear_container(self):
        """Removes all widgets from the frame."""
        for widget in self.winfo_children():
            widget.destroy()

    def show_start_menu(self):
        """Displays the initial menu to select the board size."""
        self._clear_container()
        self.board = None
        self.solution = None

        menu_frame = tk.Frame(self, bg="#2E2E2E")
        menu_frame.pack(expand=True)
        tk.Label(menu_frame, text="Flip Puzzle Solver", font=("Helvetica", 24, "bold"), bg="#2E2E2E", fg="white").pack(pady=(40, 20))
        
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
        
        # --- Back to Menu Button Added Here ---
        tk.Button(menu_frame, text="Back to Menu", font=("Helvetica", 14), command=self.show_main_menu_callback, bg="#4A4A4A", fg="white", relief="flat").pack(pady=40)

    def process_input(self):
        """Validates the user's board size input."""
        try:
            n = int(self.n_entry.get())
            if 1 < n <= 20: # Cap size for performance and usability
                self.start_puzzle_setup(n)
            else:
                self.error_label.config(text="Please enter a number between 2 and 20.")
        except ValueError:
            self.error_label.config(text="Invalid input. Please enter an integer.")

    def start_puzzle_setup(self, n):
        """Initializes the board for user input."""
        self.n = n
        self.board = [[False for _ in range(n)] for _ in range(n)]
        self.solution = None
        self.show_board_ui()

    def show_board_ui(self):
        """Displays the interactive board for setting the puzzle state."""
        self._clear_container()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(self, bg="#1E1E1E", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.canvas.bind("<Button-1>", self.handle_board_click)
        self.canvas.bind("<Configure>", lambda e: self._draw_board())

        # --- Bottom control frame ---
        control_frame = tk.Frame(self, bg="#2E2E2E")
        control_frame.grid(row=1, column=0, pady=10, sticky="ew")

        button_group = tk.Frame(control_frame, bg="#2E2E2E")
        button_group.pack(side=tk.LEFT, padx=10)

        self.solve_button = tk.Button(button_group, text="Solve", command=self.solve_puzzle, font=("Helvetica", 12, "bold"), bg="#4CAF50", fg="white", relief="flat")
        self.solve_button.pack(side=tk.LEFT, padx=10)
        tk.Button(button_group, text="Reset Board", command=lambda: self.start_puzzle_setup(self.n), font=("Helvetica", 12), bg="#FF6B6B", fg="white", relief="flat").pack(side=tk.LEFT, padx=10)
        tk.Button(button_group, text="New Size", command=self.show_start_menu, font=("Helvetica", 12), bg="#3399FF", fg="white", relief="flat").pack(side=tk.LEFT, padx=10)
        # --- NEW: Back to Menu Button Added Here ---
        tk.Button(button_group, text="Back to Menu", command=self.show_main_menu_callback, font=("Helvetica", 12), bg="#4A4A4A", fg="white", relief="flat").pack(side=tk.LEFT, padx=10)

        # --- Legend ---
        legend_frame = tk.Frame(control_frame, bg="#2E2E2E")
        legend_frame.pack(side=tk.RIGHT, padx=20)

        tk.Label(legend_frame, text="■", fg="#3399FF", bg="#2E2E2E", font=("Arial", 16)).pack(side=tk.LEFT)
        tk.Label(legend_frame, text="= On", font=("Arial", 12), bg="#2E2E2E", fg="white").pack(side=tk.LEFT, padx=(0, 15))

        tk.Label(legend_frame, text="■", fg="#3C3C3C", bg="#2E2E2E", font=("Arial", 16)).pack(side=tk.LEFT)
        tk.Label(legend_frame, text="= Off", font=("Arial", 12), bg="#2E2E2E", fg="white").pack(side=tk.LEFT, padx=(0, 15))

        tk.Label(legend_frame, text="●", fg="#E74C3C", bg="#2E2E2E", font=("Arial", 16)).pack(side=tk.LEFT)
        tk.Label(legend_frame, text="= Press", font=("Arial", 12), bg="#2E2E2E", fg="white").pack(side=tk.LEFT)

        self.status_label = tk.Label(self, text="Click tiles to set the puzzle's initial state.", font=("Helvetica", 12, "italic"), bg="#2E2E2E", fg="white")
        self.status_label.grid(row=2, column=0, pady=10)

    def _draw_board(self):
        """Renders the board and the solution, if available."""
        self.canvas.delete("all")
        cell_size = min(self.canvas.winfo_width(), self.canvas.winfo_height()) / self.n

        for r in range(self.n):
            for c in range(self.n):
                x1, y1 = c * cell_size, r * cell_size
                x2, y2 = x1 + cell_size, y1 + cell_size
                fill_color = "#3399FF" if self.board[r][c] else "#3C3C3C"
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill_color, outline="#1E1E1E", width=2)
        
        # If a solution has been found, draw the red dots
        if self.solution:
            for r in range(self.n):
                for c in range(self.n):
                    if self.solution[r][c]:
                        dot_radius = cell_size * 0.15
                        cx, cy = (c + 0.5) * cell_size, (r + 0.5) * cell_size
                        self.canvas.create_oval(cx - dot_radius, cy - dot_radius, cx + dot_radius, cy + dot_radius, fill="#E74C3C", outline="")

    def handle_board_click(self, event):
        """Toggles the state of a clicked tile."""
        if self.solution: # Clear old solution if board is modified
            self.solution = None
            self.status_label.config(text="Board modified. Click 'Solve' again.")
            
        cell_size = min(self.canvas.winfo_width(), self.canvas.winfo_height()) / self.n
        col = int(event.x // cell_size)
        row = int(event.y // cell_size)
        
        if 0 <= row < self.n and 0 <= col < self.n:
            self.board[row][col] = not self.board[row][col]
            self._draw_board()

    def solve_puzzle(self):
        """Initiates the solver and displays the result."""
        self.solve_button.config(state=tk.DISABLED)
        self.status_label.config(text="Solving...")
        self.update_idletasks() # Force UI update

        if NUMPY_AVAILABLE:
            solution_vector = self._solve_with_numpy()
        else:
            solution_vector = self._solve_with_lists()

        if solution_vector is not None:
            self.solution = [[solution_vector[r * self.n + c] for c in range(self.n)] for r in range(self.n)]
            self.status_label.config(text="Solution found! Red dots show where to press.", fg="lightgreen")
        else:
            self.solution = None
            self.status_label.config(text="This puzzle configuration is unsolvable.", fg="#FF5555")
            messagebox.showinfo("Unsolvable", "The given puzzle state cannot be solved.")
        
        self.solve_button.config(state=tk.NORMAL)
        self._draw_board()

    def _solve_with_numpy(self):
        """Solves the puzzle using Gaussian elimination with Numpy."""
        size = self.n * self.n
        # 1. Build the matrix A where A[i, j] is 1 if pressing button j affects light i
        A = np.zeros((size, size), dtype=int)
        for r in range(self.n):
            for c in range(self.n):
                idx = r * self.n + c
                A[idx, idx] = 1 # The button affects itself
                if r > 0: A[idx - self.n, idx] = 1 # North
                if r < self.n - 1: A[idx + self.n, idx] = 1 # South
                if c > 0: A[idx - 1, idx] = 1 # West
                if c < self.n - 1: A[idx + 1, idx] = 1 # East
        
        # 2. Build the vector b representing the initial board state
        b = np.array([int(val) for row in self.board for val in row])
        
        # 3. Solve the system Ax = b over GF(2)
        try:
            # Using pseudoinverse can sometimes find a solution for singular matrices
            inv_A = np.linalg.pinv(A.astype(float))
            # Perform matrix multiplication and apply modulo 2
            x = np.round(inv_A @ b.astype(float)).astype(int) % 2
            # Sanity check: verify the solution
            if np.array_equal((A @ x) % 2, b):
                return x
            else: # Fallback for complex singular cases
                return self._solve_with_lists() 
        except np.linalg.LinAlgError:
            return self._solve_with_lists() # Fallback to manual Gaussian elimination for singular matrices

    def _solve_with_lists(self):
        """Solves the puzzle using pure Python Gaussian elimination over GF(2)."""
        size = self.n * self.n
        # 1. Build the matrix A and vector b
        A = [[0] * size for _ in range(size)]
        for r in range(self.n):
            for c in range(self.n):
                idx = r * self.n + c
                A[idx][idx] = 1
                if r > 0: A[idx - self.n][idx] = 1
                if r < self.n - 1: A[idx + self.n][idx] = 1
                if c > 0: A[idx - 1][idx] = 1
                if c < self.n - 1: A[idx + 1][idx] = 1
        
        b = [int(val) for row in self.board for val in row]

        # 2. Augment matrix and perform Gaussian elimination
        for i in range(size):
            A[i].append(b[i])
        
        pivot_row = 0
        for j in range(size): # Columns
            if pivot_row >= size: break
            i = pivot_row
            while i < size and A[i][j] == 0:
                i += 1
            if i < size:
                A[pivot_row], A[i] = A[i], A[pivot_row] # Swap rows
                for k in range(pivot_row + 1, size):
                    if A[k][j] == 1:
                        for l in range(j, size + 1):
                            A[k][l] = A[k][l] ^ A[pivot_row][l] # XOR for subtraction
                pivot_row += 1
        
        # 3. Check for solvability (the sanity check)
        for i in range(pivot_row, size):
            if A[i][size] == 1: # Row is all zeros but result is 1
                return None # Unsolvable

        # 4. Back substitution
        x = [0] * size
        for i in range(pivot_row - 1, -1, -1):
            pivot_col = -1
            for j in range(size):
                if A[i][j] == 1:
                    pivot_col = j
                    break
            if pivot_col != -1:
                val = A[i][size]
                for j in range(pivot_col + 1, size):
                    val ^= (A[i][j] * x[j])
                x[pivot_col] = val
        return x