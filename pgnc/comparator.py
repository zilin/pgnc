"""PGN comparison logic for detecting differences between games."""

import chess
import chess.pgn
from typing import List, Tuple, Set
from dataclasses import dataclass

from .pgn_processor import parse_pgn, trim_game_depth, filter_game_variations
from .prefix_optimizer import optimize_variation_list
from .models import Game as GameConfig, VariationFilter


@dataclass
class ComparisonResult:
    """Result of comparing two games."""

    game1_index: int  # 1-based index in first PGN
    game2_index: int  # 1-based index in second PGN
    game1_name: str
    game2_name: str
    added_variations: List[str]  # Variations in game2 but not in game1
    removed_variations: List[str]  # Variations in game1 but not in game2
    total_variations_game1: int
    total_variations_game2: int

    def has_differences(self) -> bool:
        """Check if there are any differences between the games."""
        return len(self.added_variations) > 0 or len(self.removed_variations) > 0


def _apply_remove_variations(
    game: chess.pgn.Game,
    remove_variations: List[str]
) -> chess.pgn.Game:
    """
    Apply remove_variations to a game to create a filtered game.

    Args:
        game: Source game
        remove_variations: List of move sequences to remove

    Returns:
        Filtered game with specified variations removed
    """
    if not remove_variations:
        return game

    # Create a GameConfig with remove_variations
    variation_filters = [
        VariationFilter(moves=moves) for moves in remove_variations
    ]

    # Create a dummy GameConfig (we only need the remove_variations field)
    # Using index=1 and action="include" as defaults
    game_config = GameConfig(
        index=1,
        action="include",
        remove_variations=variation_filters
    )

    # Apply the filter
    filtered_game = filter_game_variations(game, game_config)

    return filtered_game


def extract_all_variation_paths(game: chess.pgn.Game) -> Set[str]:
    """
    Extract all variation paths from a game as move sequences.

    Uses deterministic DFS traversal (variations by index order).

    Args:
        game: Chess game to extract variations from

    Returns:
        Set of variation move sequences (e.g., {"1.e4 c5 2.Nf3 d6", ...})
    """
    variations = set()

    def traverse(node, board, moves_san=[]):
        """Deterministic DFS: iterate variations by index (0, 1, 2, ...)."""
        if not node.variations:
            # Leaf node - this is a complete variation
            formatted = _format_move_sequence(moves_san)
            variations.add(formatted)
            return

        # Traverse variations in index order (deterministic)
        for variation in node.variations:
            new_board = board.copy()
            move_san = new_board.san(variation.move)
            new_board.push(variation.move)

            traverse(variation, new_board, moves_san + [move_san])

    traverse(game, game.board())

    return variations


def _format_move_sequence(moves_san: List[str]) -> str:
    """
    Format a list of moves in SAN notation to PGN format with move numbers.

    Args:
        moves_san: List of moves in SAN notation (e.g., ["e4", "c5", "Nf3"])

    Returns:
        Formatted string (e.g., "1.e4 c5 2.Nf3")
    """
    if not moves_san:
        return ""

    formatted = []
    for i, move in enumerate(moves_san):
        if i % 2 == 0:
            # White move - add move number
            formatted.append(f"{i // 2 + 1}.{move}")
        else:
            # Black move - just the move
            formatted.append(move)

    return " ".join(formatted)


def compare_games(
    game1: chess.pgn.Game,
    game2: chess.pgn.Game,
    game1_index: int,
    game2_index: int,
    max_depth: int = None
) -> ComparisonResult:
    """
    Compare two games and identify added/removed variations.

    Args:
        game1: First game (baseline)
        game2: Second game (comparison)
        game1_index: 1-based index of game1 in its source PGN
        game2_index: 1-based index of game2 in its source PGN
        max_depth: Optional depth limit for comparison (in half-moves)

    Returns:
        ComparisonResult with differences
    """
    # Apply depth trimming if specified
    if max_depth:
        game1 = trim_game_depth(game1, max_depth)
        game2 = trim_game_depth(game2, max_depth)

    # ==================== PHASE 1: REMOVE ====================
    # Extract variation paths from both games
    variations1 = extract_all_variation_paths(game1)
    variations2 = extract_all_variation_paths(game2)

    # Find variations to remove: in game1 but NOT in game2
    to_remove = variations1 - variations2
    to_remove_list = sorted(list(to_remove))

    # Optimize remove_variations against game1 (original structure)
    optimized_removed = optimize_variation_list(to_remove_list, reference_game=game1)

    # ==================== PHASE 2: ADD ====================
    # Create intermediate game1' by applying remove_variations to game1
    game1_prime = _apply_remove_variations(game1, optimized_removed)

    # Extract variations from game1' (after removal)
    variations1_prime = extract_all_variation_paths(game1_prime)

    # Find variations to add: in game2 but NOT in game1'
    to_add = variations2 - variations1_prime
    to_add_list = sorted(list(to_add))

    # Optimize add_variations against game1' (reduced structure)
    optimized_added = optimize_variation_list(to_add_list, reference_game=game1_prime)

    # Get game names from headers
    game1_name = game1.headers.get("White", f"Game {game1_index}")
    game2_name = game2.headers.get("White", f"Game {game2_index}")

    return ComparisonResult(
        game1_index=game1_index,
        game2_index=game2_index,
        game1_name=game1_name,
        game2_name=game2_name,
        added_variations=optimized_added,
        removed_variations=optimized_removed,
        total_variations_game1=len(variations1),
        total_variations_game2=len(variations2)
    )


def compare_pgn_files(
    pgn1_path: str,
    pgn2_path: str,
    game1_idx: int = None,
    game2_idx: int = None,
    color: str = None,
    depth: int = 10
) -> List[ComparisonResult]:
    """
    Compare games from two PGN files.

    Args:
        pgn1_path: Path to first PGN file (baseline)
        pgn2_path: Path to second PGN file (comparison)
        game1_idx: Optional specific game index in pgn1 (1-based)
        game2_idx: Optional specific game index in pgn2 (1-based)
        color: Repertoire color ("white" or "black") for depth calculation
        depth: Number of move pairs to compare (default: 10)

    Returns:
        List of ComparisonResult objects (one per game pair compared)
    """
    # Parse both PGN files
    games1 = parse_pgn(pgn1_path)
    games2 = parse_pgn(pgn2_path)

    # Calculate max_depth based on color
    max_depth = None
    if color:
        if color == "white":
            max_depth = 2 * depth + 1
        else:  # black
            max_depth = 2 * depth

    results = []

    if game1_idx is not None and game2_idx is not None:
        # Compare specific games
        if game1_idx < 1 or game1_idx > len(games1):
            raise ValueError(
                f"Game index {game1_idx} out of range in {pgn1_path} "
                f"(has {len(games1)} games)"
            )
        if game2_idx < 1 or game2_idx > len(games2):
            raise ValueError(
                f"Game index {game2_idx} out of range in {pgn2_path} "
                f"(has {len(games2)} games)"
            )

        result = compare_games(
            games1[game1_idx - 1],
            games2[game2_idx - 1],
            game1_idx,
            game2_idx,
            max_depth
        )
        results.append(result)
    else:
        # Compare all games by index (1 vs 1, 2 vs 2, etc.)
        num_games = min(len(games1), len(games2))

        for i in range(num_games):
            result = compare_games(
                games1[i],
                games2[i],
                i + 1,  # 1-based index
                i + 1,  # 1-based index
                max_depth
            )
            # Only include games with differences
            if result.has_differences():
                results.append(result)

    return results
