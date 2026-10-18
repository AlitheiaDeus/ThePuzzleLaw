from collections import Counter, deque
import heapq
import sys
import argparse

class PriorityQueue:
    """
    A simple priority queue implementation using the heapq module.
    Items with lower priority values are retrieved first.
    """
    def __init__(self):
        self.elements = []
        self._counter = 0
    
    def empty(self):
        return not self.elements
    
    def put(self, item, priority):
        heapq.heappush(self.elements, (priority, self._counter, item))
        self._counter += 1
    
    def get(self):
        return heapq.heappop(self.elements)[2]

class PuzzleSolver:
    """
    Solves a sorting puzzle where items (liquids) are moved between stacks.
    
    The goal is to sort items such that each stack is either completely empty 
    or filled to its specific capacity with a single uniform item type.
    
    By default (allow_split_colors=False), items of the same type/color cannot be 
    separated across multiple stacks (e.g. 'o,o,o/o,o,o/-,-,-' is not valid).
    When allow_split_colors=True, multiple stacks may hold the same item type (legacy mode).
    
    Stacks can have different capacities in a single level.
    """
    def __init__(self, raw_data, capacities=None, allow_split_colors=False, **kwargs):
        """
        Initializes the solver with a string representation of the puzzle.
        
        Args:
            raw_data (str): A string where stacks are separated by '/' and 
                            items within a stack are separated by ','. Items
                            are listed BOTTOM-TO-TOP (base item first, top item last).
                            Use '-' as a placeholder for an empty slot (e.g. '-,-,-'
                            represents an empty stack of capacity 3, and 'l,c,-,-'
                            represents a stack of capacity 4 with base 'l' and top 'c').
            capacities (list[int], optional): Explicit list of capacities for each stack.
                            If omitted, capacities are inferred from the number of 
                            item/placeholder slots in raw_data.
            allow_split_colors (bool, optional): Whether to allow the same item type/color
                            to be separated across multiple completed stacks. Defaults to False.
                            Alias: allow_duplicate_colors.
                            
        Raises:
            ValueError: If the puzzle contains no items or stack sizes exceed capacity.
        """
        # Support alternative keyword alias allow_duplicate_colors
        if "allow_duplicate_colors" in kwargs:
            allow_split_colors = kwargs.pop("allow_duplicate_colors")
        # Defensive check in case allow_split_colors was passed as 2nd positional argument
        if isinstance(capacities, bool):
            allow_split_colors = capacities
            capacities = None

        self.allow_split_colors = bool(allow_split_colors)

        stacks = raw_data.split('/')
        self.initial_state = []
        self.capacities = []
        all_items = []
        
        for idx, stack_str in enumerate(stacks):
            tokens = [t.strip() for t in stack_str.split(',') if t.strip()]
            # Extract real items (ignore empty slot placeholder '-')
            clean_items = [t for t in tokens if t != '-']
            
            if capacities is not None and idx < len(capacities):
                cap = capacities[idx]
            else:
                cap = len(tokens) if tokens else 0
                if cap == 0 and clean_items:
                    cap = len(clean_items)
            
            if len(clean_items) > cap:
                raise ValueError(
                    f"Stack {idx+1} has {len(clean_items)} items, exceeding capacity {cap}."
                )
            
            # Input is bottom-to-top; store internally as top-to-bottom for fast pours
            self.initial_state.append(tuple(reversed(clean_items)))
            self.capacities.append(cap)
            all_items.extend(clean_items)
                
        if not all_items:
            raise ValueError("Puzzle is empty. No items found to sort.")
            
        self.item_types = set(all_items)
        self.num_stacks = len(self.initial_state)

    def can_satisfy_unique_capacities(self):
        """
        Checks if item counts can theoretically be partitioned into available stack capacities
        without separating any color into multiple stacks.
        
        Returns:
            tuple[bool, dict]: (is_possible, item_counts)
        """
        item_counts = Counter(item for stack in self.initial_state for item in stack)
        available_caps = list(self.capacities)
        for count in item_counts.values():
            if count in available_caps:
                available_caps.remove(count)
            else:
                return False, item_counts
        return True, item_counts

    def heuristic(self, state):
        """
        Calculates an admissible estimated cost (A* heuristic) to reach the goal state.
        
        To GUARANTEE finding the optimal solution path, the heuristic must NEVER
        overestimate the true remaining cost. We count the total number of color/type
        transitions between adjacent items within all stacks. Each valid move can reduce
        the total number of internal transitions by at most 1 (when a homogeneous top block
        is cleared to expose a different color below and placed onto matching color or empty space).
        The final goal state requires 0 internal transitions across all stacks.
        
        Args:
            state (tuple): The current board state.
            
        Returns:
            int: A mathematically safe lower-bound estimate of remaining moves.
        """
        transitions = 0
        for stack in state:
            for i in range(1, len(stack)):
                if stack[i] != stack[i-1]:
                    transitions += 1
        return transitions

    def get_moves(self, state):
        """
        Generates all valid and optimized moves from the current state.
        
        Supports partial pours (splitting the top block if target stack space is limited),
        applies symmetry breaking for empty stacks of identical capacities, and prevents
        redundant moves out of completed stacks.
        
        Args:
            state (tuple): The current board state.
            
        Returns:
            list: A list of tuples containing (new_state, move_description).
        """
        possible_moves = []
        
        # Symmetry breaking: Find the first available empty stack for each capacity
        first_empty_by_cap = {}
        for j, target_stack in enumerate(state):
            if len(target_stack) == 0:
                cap = self.capacities[j]
                if cap not in first_empty_by_cap:
                    first_empty_by_cap[cap] = j

        for i, source_stack in enumerate(state):
            if not source_stack:
                continue
            
            cap_i = self.capacities[i]
            top_type = source_stack[0]
            block_size = 0
            
            # Determine how many identical items are on top of the source stack
            for piece in source_stack:
                if piece == top_type:
                    block_size += 1
                else:
                    break

            for j, target_stack in enumerate(state):
                if i == j:
                    continue
                
                cap_j = self.capacities[j]
                is_empty = len(target_stack) == 0
                
                # Symmetry breaking: if target is empty, only allow moving to the first empty stack of this capacity.
                if is_empty and j != first_empty_by_cap.get(cap_j):
                    continue
                
                same_type = not is_empty and target_stack[0] == top_type
                
                if is_empty or same_type:
                    available_space = cap_j - len(target_stack)
                    
                    if available_space > 0:
                        # Liquid pouring: pour as much as fits (partial pour if space < block_size)
                        move_size = min(block_size, available_space)
                        
                        # Optimization: Prevent moving an entire homogeneous stack into an empty stack of equal capacity
                        if is_empty and move_size == len(source_stack) and cap_j == cap_i:
                            continue
                            
                        move_block = source_stack[:move_size]
                        remaining_source = source_stack[move_size:]
                        
                        # Create the new state after the move
                        new_state = list(state)
                        new_state[i] = tuple(remaining_source)
                        new_state[j] = tuple(move_block) + target_stack
                        
                        move_desc = f"{i+1} -> {j+1}"
                        possible_moves.append((tuple(new_state), move_desc))
        
        return possible_moves

    def is_goal(self, state, allow_split_colors=None):
        """
        Evaluates whether the given state satisfies all goal conditions.
        
        The goal is met when all stacks are either completely empty or 
        filled to capacity with a single uniform item type.
        
        If allow_split_colors is False (default), no two stacks may contain
        the same item type (items of a color cannot be separated into multiple columns).
        If allow_split_colors is True, multiple stacks may hold the same item type.
        
        Args:
            state (tuple): The current board state.
            allow_split_colors (bool, optional): Override for allow_split_colors setting.
            
        Returns:
            bool: True if the state is the goal, False otherwise.
        """
        split_allowed = self.allow_split_colors if allow_split_colors is None else allow_split_colors
        seen_types = set()
        for i, stack in enumerate(state):
            if not stack:
                continue
            # Verify the stack is filled to its capacity
            if len(stack) != self.capacities[i]:
                return False
            # Verify the stack contains only one type of item
            if len(set(stack)) > 1:
                return False
            # Verify no two stacks share the same color if split colors are disallowed
            if not split_allowed:
                item_type = stack[0]
                if item_type in seen_types:
                    return False
                seen_types.add(item_type)
        return True

    def solve(self, allow_split_colors=None):
        """
        Executes the A* Search algorithm to find the optimal solution path.
        
        Uses normalized state tuples tagged with each stack's capacity to 
        safely eliminate identical symmetrical permutations across stacks of the same capacity.
        
        Args:
            allow_split_colors (bool, optional): Override for allow_split_colors setting.
            
        Returns:
            list or None: A list of string move descriptions if a solution is found, 
                          or None if the puzzle is unsolvable.
        """
        split_allowed = self.allow_split_colors if allow_split_colors is None else allow_split_colors
        
        # Fast early pruning: if colors cannot be split, item counts must match available stack capacities
        if not split_allowed:
            possible, _ = self.can_satisfy_unique_capacities()
            if not possible:
                return None

        start_state = tuple(self.initial_state)
        
        frontier = PriorityQueue()
        frontier.put((start_state, []), 0)
        
        def normalize_state(st):
            # Pair each stack with its capacity so stacks of different capacities
            # are not conflated, while symmetrical stacks of the same capacity are grouped.
            return tuple(sorted((self.capacities[idx], st[idx]) for idx in range(len(st))))
        
        start_normalized = normalize_state(start_state)
        cost_so_far = {start_normalized: 0}

        while not frontier.empty():
            current_state, path = frontier.get()

            if self.is_goal(current_state, allow_split_colors=split_allowed):
                return path

            for next_state, move_desc in self.get_moves(current_state):
                new_cost = len(path) + 1
                next_normalized = normalize_state(next_state)
                
                if next_normalized not in cost_so_far or new_cost < cost_so_far[next_normalized]:
                    cost_so_far[next_normalized] = new_cost
                    priority = new_cost + self.heuristic(next_state)
                    frontier.put((next_state, path + [move_desc]), priority)
        
        return None 

def repl(default_allow_split_colors=False):
    """
    Runs an interactive Read-Eval-Print Loop (REPL) for the puzzle solver.
    
    Args:
        default_allow_split_colors (bool): Initial state for allowing duplicate color columns.
    """
    allow_split = bool(default_allow_split_colors)

    def print_banner():
        print("=" * 64)
        print("           LIQUIDS PUZZLE SOLVER - INTERACTIVE REPL             ")
        print("=" * 64)
        print("Format: Separate stacks with '/', items with ',' (BOTTOM-TO-TOP).")
        print("        Use '-' for empty slots (e.g. 'l,c,-,-' for 4-cap stack).")
        mode_str = "ALLOWED (Loophole mode)" if allow_split else "DISALLOWED (Cannot separate colors)"
        print(f"Rule:   Split colors across columns = {mode_str}")
        print("Commands: 'mode' (toggle rule), 'example', 'help', 'exit' or 'quit'")
        print("=" * 64)

    print_banner()

    while True:
        try:
            mode_tag = "[split:ON]" if allow_split else "[split:OFF]"
            user_input = input(f"\n{mode_tag} Enter puzzle > ").strip()
            if not user_input:
                continue

            cmd = user_input.lower()
            if cmd in ("exit", "quit", "q"):
                print("Exiting solver. Goodbye!")
                break
            elif cmd in ("mode", "toggle", "toggle-split", "split"):
                allow_split = not allow_split
                mode_desc = (
                    "TRUE (Colors CAN be separated into multiple columns - loophole mode)"
                    if allow_split
                    else "FALSE (Colors CANNOT be separated into multiple columns - strict mode)"
                )
                print(f"\n[Rule Updated]")
                print(f"  allow_split_colors is now: {mode_desc}")
                continue
            elif cmd == "help":
                print("\n[Help & Usage]")
                print("  - Stacks are separated by '/'")
                print("  - Items are entered BOTTOM-TO-TOP (base item first, top item last)")
                print("  - '-' represents an empty slot")
                print("  - Example: l,c,-,- / w,n,-,- / l,n,l,w / -,-,-")
                print("    ('l,c,-,-' means 'l' is at bottom, 'c' is on top, and 2 empty spaces above)")
                print("  - 'mode' or 'toggle' : Toggle whether colors can be separated across columns.")
                print(f"                         Currently: allow_split_colors = {allow_split}")
                print("  - 'example'          : Run a built-in demo puzzle.")
                print("  - 'exit' or 'quit'   : Exit the REPL.")
                continue
            elif cmd == "example":
                user_input = "w,n,-,- / c,n,-,- / c,l,-,- / c,w,-,- / l,n,l,w / c,l,n,w / -,-,-"
                print(f"Running built-in example:\n{user_input}")

            solver = PuzzleSolver(user_input, allow_split_colors=allow_split)
            print(f"\n[Puzzle Configuration]")
            print(f"  Item types   : {', '.join(sorted(solver.item_types))}")
            split_status = "Allowed (Loophole)" if allow_split else "Disallowed (Strict: 1 col per color)"
            print(f"  Split colors : {split_status}")
            print(f"  Stacks ({solver.num_stacks}):")
            for idx, (st, cap) in enumerate(zip(solver.initial_state, solver.capacities), 1):
                bottom_up = list(reversed(st))
                items_str = ", ".join(bottom_up) if bottom_up else "(empty)"
                top_str = f"top: '{st[0]}'" if st else "empty"
                print(f"    Stack {idx} [cap {cap}]: [{items_str}] -> ({top_str})")

            print("\nSolving puzzle using A* search...")
            result_path = solver.solve()

            if result_path is None:
                if not allow_split:
                    can_satisfy, counts = solver.can_satisfy_unique_capacities()
                    if not can_satisfy:
                        print("Result: No solution found under strict mode (split colors disallowed).")
                        counts_str = ", ".join(f"'{k}': {v}" for k, v in sorted(counts.items()))
                        print(f"Reason: Item counts [{counts_str}] cannot match available capacities {solver.capacities}.")
                        print("Tip: If this puzzle allows separating colours into multiple columns,")
                        print("     type 'mode' to toggle allow_split_colors to True and solve again.")
                    else:
                        print("Result: No solution found. The puzzle might be impossible.")
                else:
                    print("Result: No solution found. The puzzle might be impossible.")
            else:
                if len(result_path) == 0:
                    print("Result: Already in a completed goal state (0 moves needed).")
                else:
                    print(f"Result: Solution found in {len(result_path)} moves:")
                    for step, move in enumerate(result_path, 1):
                        print(f"  Step {step:2d}: Move {move}")
        except ValueError as e:
            print(f"Error: {e}")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting solver. Goodbye!")
            break

def main():
    parser = argparse.ArgumentParser(
        description="Liquid / Water Sort Puzzle Solver using A* Search."
    )
    parser.add_argument(
        "puzzle",
        nargs="?",
        default=None,
        help="Optional puzzle string to solve directly (e.g. 'o,o,o/o,o,o/-,-,-'). If omitted, starts REPL."
    )
    parser.add_argument(
        "--allow-split-colors",
        "--allow-duplicate-colors",
        "--split",
        dest="allow_split",
        action="store_true",
        default=False,
        help="Allow the same color/item type to be separated across multiple completed columns (legacy loophole mode)."
    )
    # Ensure puzzle strings starting with '-' (e.g. '-,-,-/...') are not misinterpreted as CLI flags
    processed_argv = []
    for arg in sys.argv[1:]:
        if "/" in arg and not arg.startswith("--"):
            processed_argv.extend(["--", arg])
        else:
            processed_argv.append(arg)
    args = parser.parse_args(processed_argv)

    if args.puzzle:
        try:
            solver = PuzzleSolver(args.puzzle, allow_split_colors=args.allow_split)
            print(f"Puzzle: {args.puzzle}")
            print(f"Allow split colors: {args.allow_split}")
            print("Solving...")
            res = solver.solve()
            if res is None:
                print("Result: No solution found.")
                sys.exit(1)
            elif len(res) == 0:
                print("Result: Already solved (0 moves).")
            else:
                print(f"Result: Solved in {len(res)} moves:")
                for step, move in enumerate(res, 1):
                    print(f"  Step {step:2d}: Move {move}")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        repl(default_allow_split_colors=args.allow_split)

if __name__ == "__main__":
    main()