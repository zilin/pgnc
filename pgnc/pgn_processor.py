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
    skip_filters: Optional[List[VariationFilter]],
    keep_filters: Optional[List[VariationFilter]],
) -> bool:
    """
    Determine if a variation should be skipped based on filters.

    Args:
        move_path: Current variation's move sequence
        skip_filters: Blacklist filters (skip if matches)
        keep_filters: Whitelist filters (skip if doesn't match)

    Returns:
        True if variation should be skipped
    """
    # Whitelist approach: keep only if matches
    if keep_filters:
        for keep_filter in keep_filters:
            try:
                pattern_moves = parse_move_sequence(keep_filter.moves)
                if matches_variation_pattern(move_path, pattern_moves):
                    # Check depth constraint if specified
                    if keep_filter.depth and len(move_path) > keep_filter.depth:
                        continue
                    return False  # Keep this variation
            except ValueError:
                # Invalid move sequence in filter, skip it
                continue
        return True  # Didn't match any keep filter, so skip

    # Blacklist approach: skip if matches
    if skip_filters:
        for skip_filter in skip_filters:
            try:
                pattern_moves = parse_move_sequence(skip_filter.moves)
                if matches_variation_pattern(move_path, pattern_moves):
                    # Check depth constraint if specified
                    if skip_filter.depth and len(move_path) <= skip_filter.depth:
                        continue
                    return True  # Skip this variation
            except ValueError:
                # Invalid move sequence in filter, skip it
                continue

    return False  # Don't skip by default


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
                new_path, game_config.skip_variations, game_config.keep_variations
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

    return filtered


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

    Args:
        game: Game to count variations in

    Returns:
        Total number of variations
    """
    if game is None:
        return 0

    count = 0

    def traverse(node):
        nonlocal count
        for variation in node.variations:
            count += 1
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
