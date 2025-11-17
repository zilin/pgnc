"""Prefix tree optimization for variation lists."""

import chess
import chess.pgn
from typing import List, Set, Dict, Tuple
from dataclasses import dataclass, field


@dataclass
class PrefixNode:
    """Node in the prefix tree."""

    move: str = None  # SAN notation (e.g., "e4", "Nf3")
    children: Dict[str, 'PrefixNode'] = field(default_factory=dict)
    is_leaf: bool = False  # True if this path appears in the variation list
    traversal_order: int = -1  # Order from game tree DFS traversal


class PrefixTree:
    """Prefix tree for variation move sequences."""

    def __init__(self):
        self.root = PrefixNode()

    def insert(self, moves: List[str]):
        """Insert a move sequence into the tree."""
        node = self.root
        for move in moves:
            if move not in node.children:
                node.children[move] = PrefixNode(move=move)
            node = node.children[move]
        node.is_leaf = True

    def find_minimal_covering_set(self) -> List[List[str]]:
        """
        Find minimal set of prefixes that cover all leaf nodes.

        Returns:
            List of move sequences (as lists) representing the minimal covering set
        """
        covering_set = []

        def traverse(node: PrefixNode, path: List[str]):
            """DFS to find minimal covering nodes."""
            if not node.children:
                # Leaf node with no children - must include it
                if node.is_leaf:
                    covering_set.append(path[:])
                return

            # Check if all descendants of this node are in the variation list
            all_descendants_are_leaves = self._all_descendants_are_leaves(node)

            if all_descendants_are_leaves:
                # All variations under this node are being removed
                # Use this node as the covering point (even if it wasn't explicitly in the list)
                covering_set.append(path[:])
                return

            # Otherwise, recurse into children
            for move, child in node.children.items():
                traverse(child, path + [move])

        # Start traversal from root's children
        for move, child in self.root.children.items():
            traverse(child, [move])

        return covering_set

    def find_minimal_covering_set_validated(
        self,
        variations_to_remove: Set[str],
        all_game_variations: Set[str]
    ) -> List[List[str]]:
        """
        Find minimal set of prefixes that cover variations, validated against original game.

        This checks that ALL variations in the original game matching a prefix
        are being removed before using that prefix as a covering point.

        Args:
            variations_to_remove: Set of variation strings being removed
            all_game_variations: Set of ALL variation strings in the original game

        Returns:
            List of move sequences (as lists) representing the minimal covering set
        """
        covering_set = []

        def traverse(node: PrefixNode, path: List[str]):
            """DFS to find minimal covering nodes with validation."""
            if not node.children:
                # Leaf node with no children - must include it
                if node.is_leaf:
                    covering_set.append(path[:])
                return

            # Check if we can use this node as a covering point
            # by verifying ALL game variations with this prefix are being removed
            if all_game_variations and self._can_use_as_covering_point(
                path, variations_to_remove, all_game_variations
            ):
                # All variations in the original game with this prefix are being removed
                covering_set.append(path[:])
                return

            # Otherwise, recurse into children
            for move, child in node.children.items():
                traverse(child, path + [move])

        # Start traversal from root's children
        for move, child in self.root.children.items():
            traverse(child, [move])

        return covering_set

    def _can_use_as_covering_point(
        self,
        prefix_moves: List[str],
        variations_to_remove: Set[str],
        all_game_variations: Set[str]
    ) -> bool:
        """
        Check if a prefix can be used as a covering point.

        Returns True only if ALL variations in the original game that start
        with this prefix are in the removal set.

        Args:
            prefix_moves: The prefix move sequence to check
            variations_to_remove: Set of variations being removed
            all_game_variations: Set of all variations in the game

        Returns:
            True if this prefix covers all matching variations
        """
        prefix_str = _format_move_list_to_pgn(prefix_moves)

        # Find all variations in the game that start with this prefix
        # Use proper prefix matching (must be followed by space or end of string)
        matching_game_vars = []
        for game_var in all_game_variations:
            if game_var == prefix_str or game_var.startswith(prefix_str + " "):
                matching_game_vars.append(game_var)

        if not matching_game_vars:
            # No variations in game match this prefix - shouldn't happen
            return False

        # Check if ALL matching variations are in the removal set
        for game_var in matching_game_vars:
            if game_var not in variations_to_remove:
                # Found a variation in the game that's NOT being removed
                return False

        # All matching variations are being removed - can use this prefix
        return True

    def _all_descendants_are_leaves(self, node: PrefixNode) -> bool:
        """Check if all descendants of this node are marked as leaves."""
        if not node.children:
            return node.is_leaf

        # Check all children recursively
        for child in node.children.values():
            if not self._all_descendants_are_leaves(child):
                return False

        return True


def parse_move_sequence_to_list(move_string: str) -> List[str]:
    """
    Parse a PGN move sequence string into a list of moves.

    Args:
        move_string: String like "1.e4 c5 2.Nf3 d6"

    Returns:
        List of moves like ["e4", "c5", "Nf3", "d6"]
    """
    moves = []
    tokens = move_string.replace(".", " ").split()

    for token in tokens:
        token = token.strip()
        if not token or token.isdigit():
            continue
        moves.append(token)

    return moves


def optimize_variation_list(
    variations: List[str],
    reference_game: chess.pgn.Game = None
) -> List[str]:
    """
    Optimize a list of variation move sequences by finding minimal covering set.

    Args:
        variations: List of move sequences (e.g., ["1.e4 c5 2.Nf3", "1.e4 e5"])
        reference_game: Optional game for determining traversal order AND validation

    Returns:
        Optimized list of move sequences (minimal covering set, deterministically ordered)
    """
    if not variations:
        return []

    # Get all variations from the reference game if provided
    all_game_variations = set()
    if reference_game:
        all_game_variations = _extract_all_variation_paths_from_game(reference_game)

    # Build prefix tree
    tree = PrefixTree()
    variations_set = set(variations)
    for var_string in variations:
        moves = parse_move_sequence_to_list(var_string)
        tree.insert(moves)

    # Find minimal covering set
    covering_set = tree.find_minimal_covering_set_validated(
        variations_set, all_game_variations
    )

    # Sort alphabetically for deterministic output
    covering_set.sort()

    # Convert back to PGN format with move numbers
    optimized = []
    for moves in covering_set:
        formatted = _format_move_list_to_pgn(moves)
        optimized.append(formatted)

    return optimized


def _extract_all_variation_paths_from_game(game: chess.pgn.Game) -> Set[str]:
    """
    Extract all variation paths from a game as formatted strings.

    Args:
        game: Chess game to extract variations from

    Returns:
        Set of variation move sequences (e.g., {"1.e4 c5 2.Nf3 d6", ...})
    """
    variations = set()

    def traverse(node, board, moves_san=[]):
        """DFS to extract all variation paths."""
        if not node.variations:
            # Leaf node - this is a complete variation
            formatted = _format_move_list_to_pgn(moves_san)
            variations.add(formatted)
            return

        # Traverse children
        for variation in node.variations:
            new_board = board.copy()
            move_san = new_board.san(variation.move)
            new_board.push(variation.move)

            traverse(variation, new_board, moves_san + [move_san])

    traverse(game, game.board())

    return variations


def _format_move_list_to_pgn(moves: List[str]) -> str:
    """
    Format a list of moves to PGN notation with move numbers.

    Args:
        moves: List of moves like ["e4", "c5", "Nf3"]

    Returns:
        Formatted string like "1.e4 c5 2.Nf3"
    """
    formatted = []
    for i, move in enumerate(moves):
        if i % 2 == 0:
            # White move - add move number
            formatted.append(f"{i // 2 + 1}.{move}")
        else:
            # Black move - just the move
            formatted.append(move)

    return " ".join(formatted)
