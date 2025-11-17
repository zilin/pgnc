"""PGN parsing, filtering, and processing."""

import chess
import chess.pgn
from typing import List, Optional, Tuple
from io import StringIO

from .models import Game as GameConfig, VariationFilter


def parse_pgn(pgn_path: str) -> List[chess.pgn.Game]:
    """
    Parse PGN file and return list of games.

    Args:
        pgn_path: Path to PGN file

    Returns:
        List of chess.pgn.Game objects
    """
    games = []
    with open(pgn_path, "r") as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break
            games.append(game)

    return games


def parse_move_sequence(move_string: str) -> List[chess.Move]:
    """
    Parse a move sequence in SAN notation into chess.Move objects.

    Args:
        move_string: Move sequence like "1.e4 c5 2.Nf3 d6"

    Returns:
        List of chess.Move objects

    Raises:
        ValueError: If move sequence is invalid
    """
    board = chess.Board()
    moves = []

    # Clean up move string: remove move numbers, extra spaces
    tokens = move_string.replace(".", " ").split()

    for token in tokens:
        token = token.strip()
        if not token or token.isdigit():
            continue

        try:
            move = board.parse_san(token)
            moves.append(move)
            board.push(move)
        except (ValueError, chess.IllegalMoveError, chess.InvalidMoveError) as e:
            raise ValueError(f"Invalid move '{token}' in sequence '{move_string}': {e}")

    return moves


def matches_variation_pattern(
    move_path: List[chess.Move], pattern_moves: List[chess.Move]
) -> bool:
    """
    Check if move path starts with the pattern moves.

    Args:
        move_path: Current variation's move sequence
        pattern_moves: Pattern to match against

    Returns:
        True if move_path starts with pattern_moves
    """
    if len(move_path) < len(pattern_moves):
        return False

    for i, pattern_move in enumerate(pattern_moves):
        if move_path[i] != pattern_move:
            return False

    return True


def should_skip_variation(
    move_path: List[chess.Move],
    remove_filters: Optional[List[VariationFilter]],
    add_filters: Optional[List[VariationFilter]],
) -> bool:
    """
    Determine if a variation should be skipped based on filters.

    Logic: result = (all - removed) ∪ added
    - If variation matches remove_filters: skip it
    - If variation matches add_filters: keep it (even if it was removed)
    - Otherwise: keep it (default)

    Args:
        move_path: Current variation's move sequence
        remove_filters: Variations to remove from source
        add_filters: Variations to add (overrides removal)

    Returns:
        True if variation should be skipped
    """
    should_remove = False
    should_add = False

    # Check if variation matches remove filters
    if remove_filters:
        for remove_filter in remove_filters:
            try:
                pattern_moves = parse_move_sequence(remove_filter.moves)
                if matches_variation_pattern(move_path, pattern_moves):
                    # Check depth constraint if specified
                    if remove_filter.depth and len(move_path) <= remove_filter.depth:
                        continue
                    should_remove = True
                    break
            except ValueError:
                # Invalid move sequence in filter, skip it
                continue

    # Check if variation matches add filters
    if add_filters:
        for add_filter in add_filters:
            try:
                pattern_moves = parse_move_sequence(add_filter.moves)
                if matches_variation_pattern(move_path, pattern_moves):
                    # Check depth constraint if specified
                    if add_filter.depth and len(move_path) > add_filter.depth:
                        continue
                    should_add = True
                    break
            except ValueError:
                # Invalid move sequence in filter, skip it
                continue

    # Union logic: (all - removed) ∪ added
    # - If should_add: keep it (add overrides remove)
    # - If should_remove and not should_add: skip it
    # - Otherwise: keep it (default)
    if should_add:
        return False  # Keep it (in the added set)
    elif should_remove:
        return True   # Skip it (removed and not added back)
    else:
        return False  # Keep it (default - in the "all" set)


def filter_game_variations(
    game: chess.pgn.Game, game_config: GameConfig
) -> chess.pgn.Game:
    """
    Filter variations in a game based on configuration.

    Args:
        game: Source game with variations
        game_config: Configuration for filtering

    Returns:
        New game with filtered variations
    """
    if game_config.action == "skip":
        return None

    if game_config.action == "skip_keep_headers":
        # Create empty game with just headers
        filtered = chess.pgn.Game()
        copy_headers(game, filtered)
        return filtered

    # Create new game and copy headers
    filtered = chess.pgn.Game()
    copy_headers(game, filtered)

    # Traverse and filter variations
    def traverse_and_filter(src_node, dst_node, current_path=[]):
        """Recursively traverse game tree and filter variations."""
        variations_added = 0

        for variation in src_node.variations:
            new_path = current_path + [variation.move]

            # Check if this variation should be skipped
            if should_skip_variation(
                new_path, game_config.remove_variations, game_config.add_variations
            ):
                continue

            # Keep this variation
            new_node = dst_node.add_variation(variation.move)

            # Copy comments and annotations
            if variation.comment:
                new_node.comment = variation.comment
            if variation.nags:
                new_node.nags = variation.nags.copy()

            variations_added += 1

            # Recurse to child variations
            traverse_and_filter(variation, new_node, new_path)

        return variations_added

    traverse_and_filter(game, filtered)

    # Add variations that don't exist in the source
    if game_config.add_variations:
        for add_filter in game_config.add_variations:
            try:
                moves = parse_move_sequence(add_filter.moves)
                _add_variation_to_game(filtered, moves)
            except ValueError:
                # Invalid move sequence, skip it
                continue

    return filtered


def _add_variation_to_game(game: chess.pgn.Game, moves: List[chess.Move]):
    """
    Add a variation to a game, constructing the path if it doesn't exist.

    Args:
        game: Game to add variation to
        moves: Sequence of moves to add
    """
    if not moves:
        return

    current_node = game
    board = game.board()

    for move in moves:
        # Check if this move already exists as a variation
        existing_var = None
        for variation in current_node.variations:
            if variation.move == move:
                existing_var = variation
                break

        if existing_var:
            # Move already exists, continue down this path
            current_node = existing_var
            board.push(move)
        else:
            # Move doesn't exist, create it
            current_node = current_node.add_variation(move)
            board.push(move)


def trim_game_depth(game: chess.pgn.Game, max_depth: int) -> chess.pgn.Game:
    """
    Trim all variations in a game to maximum depth.

    Args:
        game: Source game
        max_depth: Maximum number of half-moves (plies) to keep

    Returns:
        New game with trimmed variations
    """
    if game is None:
        return None

    trimmed = chess.pgn.Game()
    copy_headers(game, trimmed)

    def traverse_and_trim(src_node, dst_node, depth=0):
        """Recursively traverse and trim to max depth."""
        if depth >= max_depth:
            # Reached max depth, stop here
            # Preserve any comment at this position
            if src_node.comment:
                dst_node.comment = src_node.comment
            return

        for variation in src_node.variations:
            new_node = dst_node.add_variation(variation.move)

            # Copy comments and annotations
            if variation.comment:
                new_node.comment = variation.comment
            if variation.nags:
                new_node.nags = variation.nags.copy()

            # Recurse
            traverse_and_trim(variation, new_node, depth + 1)

    traverse_and_trim(game, trimmed)

    return trimmed


def copy_headers(src_game: chess.pgn.Game, dst_game: chess.pgn.Game):
    """Copy all headers from source game to destination game."""
    for key, value in src_game.headers.items():
        dst_game.headers[key] = value


def count_variations(game: chess.pgn.Game) -> int:
    """
    Count total number of variations in a game.
    
    A variation is defined as a unique path from the root node to a leaf node.
    This counts the number of leaf nodes in the game tree.

    Args:
        game: Game to count variations in

    Returns:
        Total number of variations (leaf nodes)
    """
    if game is None:
        return 0

    count = 0

    def traverse(node):
        nonlocal count
        if not list(node.variations):
            # Leaf node - this is a complete variation
            count += 1
            return
        
        # Recurse into all variations
        for variation in node.variations:
            traverse(variation)

    traverse(game)
    return count


def get_average_depth(game: chess.pgn.Game) -> float:
    """
    Calculate average depth of all variations in a game.

    Args:
        game: Game to analyze

    Returns:
        Average depth in half-moves
    """
    if game is None:
        return 0.0

    depths = []

    def traverse(node, depth=0):
        if not list(node.variations):
            # Leaf node
            depths.append(depth)
            return

        for variation in node.variations:
            traverse(variation, depth + 1)

    traverse(game)

    return sum(depths) / len(depths) if depths else 0.0


def write_pgn(games: List[chess.pgn.Game], output_path: str, add_metadata: bool = True):
    """
    Write games to PGN file.

    Args:
        games: List of games to write
        output_path: Output file path
        add_metadata: Whether to add curation metadata comment
    """
    with open(output_path, "w") as f:
        for i, game in enumerate(games):
            if game is None:
                continue

            # Add curation metadata if requested
            if add_metadata and i == 0:
                # Add to first game's headers
                if "Curator" not in game.headers:
                    game.headers["Curator"] = "pgn-curator v0.1.0"

            # Write game
            exporter = chess.pgn.StringExporter(
                headers=True, variations=True, comments=True
            )
            pgn_string = game.accept(exporter)
            f.write(pgn_string)
            f.write("\n\n")
