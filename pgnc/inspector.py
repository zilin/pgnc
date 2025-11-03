"""PGN file inspection and analysis."""

import chess
import chess.pgn
from typing import List, Dict, Tuple
from rich.console import Console
from rich.table import Table

from .pgn_processor import parse_pgn, count_variations, get_average_depth


console = Console()


def inspect_pgn(pgn_path: str, game_index: int = None, list_variations: bool = False):
    """
    Inspect PGN file and display structure and statistics.

    Args:
        pgn_path: Path to PGN file
        game_index: If specified, show details for specific game only
        list_variations: If True, list all variation move sequences
    """
    console.print(f"\n[cyan]File:[/cyan] {pgn_path}\n")

    # Parse PGN
    games = parse_pgn(pgn_path)

    if not games:
        console.print("[yellow]No games found in PGN file[/yellow]")
        return

    # Show specific game details
    if game_index is not None:
        if game_index < 1 or game_index > len(games):
            console.print(
                f"[red]Error:[/red] Game index {game_index} out of range "
                f"(file has {len(games)} games, indices 1-{len(games)})"
            )
            return

        # Convert 1-based to 0-based for internal use
        _inspect_single_game(games[game_index - 1], game_index - 1, list_variations)
        return

    # Show summary of all games
    _inspect_all_games(games)


def _inspect_all_games(games: List[chess.pgn.Game]):
    """Display summary of all games in PGN."""

    total_variations = 0
    total_depth = 0.0
    max_depth_overall = 0

    console.print(f"[bold]Games:[/bold]\n")

    for i, game in enumerate(games):
        variations = count_variations(game)
        avg_depth = get_average_depth(game)
        max_depth = _get_max_depth(game)

        total_variations += variations
        total_depth += avg_depth
        max_depth_overall = max(max_depth_overall, max_depth)

        # Extract game info
        white = game.headers.get("White", "?")
        eco = game.headers.get("ECO", "?")
        annotator = game.headers.get("Annotator", "?")

        # Display game summary
        console.print(f"  [bold cyan][{i + 1}][/bold cyan] {white}")
        console.print(f"      Variations: {variations}")
        console.print(
            f"      Avg Depth: {avg_depth:.1f} moves, Max Depth: {max_depth} moves"
        )
        console.print(f"      ECO: {eco}")
        if annotator != "?":
            console.print(f"      Annotator: {annotator}")
        console.print()

    # Overall statistics
    console.print(
        f"[bold]Total:[/bold] {len(games)} game(s), {total_variations} variations"
    )
    if len(games) > 0:
        avg_variations = total_variations / len(games)
        avg_depth_overall = total_depth / len(games)
        console.print(
            f"[bold]Average:[/bold] {avg_variations:.0f} variations per game, "
            f"{avg_depth_overall:.1f} moves depth"
        )
        console.print(f"[bold]Max Depth:[/bold] {max_depth_overall} moves")


def _inspect_single_game(game: chess.pgn.Game, index: int, list_variations: bool):
    """Display detailed information about a single game."""

    white = game.headers.get("White", "?")
    eco = game.headers.get("ECO", "?")

    console.print(f"[bold cyan]Game [{index + 1}]:[/bold cyan] {white}")
    console.print(f"[bold]ECO:[/bold] {eco}\n")

    # Headers
    console.print("[bold]Headers:[/bold]")
    for key, value in game.headers.items():
        console.print(f"  {key}: {value}")
    console.print()

    # Statistics
    variations = count_variations(game)
    avg_depth = get_average_depth(game)
    max_depth = _get_max_depth(game)

    console.print(f"[bold]Variations:[/bold] {variations}")
    console.print(f"[bold]Average Depth:[/bold] {avg_depth:.1f} moves")
    console.print(f"[bold]Max Depth:[/bold] {max_depth} moves\n")

    # First moves
    first_moves = _get_first_moves(game, limit=5)
    if first_moves:
        console.print("[bold]Opening moves:[/bold]")
        console.print(f"  {first_moves}\n")

    # List all variations if requested
    if list_variations:
        console.print("[bold]All Variations:[/bold]\n")
        variations_list = _extract_all_variations(game)

        for i, (moves_san, depth) in enumerate(variations_list, 1):
            console.print(f"  {i}. {moves_san} [dim](depth: {depth})[/dim]")


def _get_max_depth(game: chess.pgn.Game) -> int:
    """Get maximum depth of any variation in the game."""
    max_depth = 0

    def traverse(node, depth=0):
        nonlocal max_depth
        max_depth = max(max_depth, depth)
        for variation in node.variations:
            traverse(variation, depth + 1)

    traverse(game)
    return max_depth


def _get_first_moves(game: chess.pgn.Game, limit: int = 10) -> str:
    """Get first N moves of the main line."""
    board = game.board()
    moves = []
    node = game

    for _ in range(limit):
        if not node.variations:
            break
        node = node.variation(0)
        moves.append(board.san(node.move))
        board.push(node.move)

    # Format with move numbers
    formatted = []
    for i, move in enumerate(moves):
        if i % 2 == 0:
            formatted.append(f"{i // 2 + 1}.{move}")
        else:
            formatted.append(move)

    return " ".join(formatted)


def _extract_all_variations(game: chess.pgn.Game) -> List[Tuple[str, int]]:
    """
    Extract all variations as move sequences.

    Returns:
        List of (move_sequence, depth) tuples
    """
    variations = []

    def traverse(node, board, moves_san=[], depth=0):
        if not node.variations:
            # Leaf node - this is a complete variation
            variations.append((" ".join(moves_san), depth))
            return

        for variation in node.variations:
            new_board = board.copy()
            move_san = new_board.san(variation.move)
            new_board.push(variation.move)

            traverse(variation, new_board, moves_san + [move_san], depth + 1)

    traverse(game, game.board())

    return variations


def generate_starter_config(pgn_path: str, output_path: str = None):
    """
    Generate a starter configuration file from PGN.

    Args:
        pgn_path: Path to source PGN file
        output_path: Path for output config (default: <pgn_name>_config.yaml)
    """
    import yaml
    from pathlib import Path

    if output_path is None:
        pgn_name = Path(pgn_path).stem
        output_path = f"{pgn_name}_config.yaml"

    # Parse PGN
    games = parse_pgn(pgn_path)

    # Build config structure
    config = {
        "name": f"Repertoire from {Path(pgn_path).name}",
        "description": "Auto-generated starter config - edit as needed",
        "source": pgn_path,
        "output": f"{Path(pgn_path).stem}_curated.pgn",
        "settings": {
            "max_depth": 14,
            "preserve_comments": True,
            "add_curation_comment": True,
        },
        "games": [],
    }

    # Add all games with include action
    for i, game in enumerate(games):
        white = game.headers.get("White", f"Game {i + 1}")
        variations = count_variations(game)

        config["games"].append(
            {
                "index": i + 1,  # 1-based indexing (as per project convention)
                "action": "include",
                "name": f"{white} ({variations} variations)",
            }
        )

    # Write config
    with open(output_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    console.print(f"[green]✓[/green] Generated starter config: {output_path}")
    console.print(f"\nEdit this file to:")
    console.print("  - Change actions to 'skip' or 'skip_keep_headers'")
    console.print("  - Add skip_variations or keep_variations")
    console.print("  - Adjust max_depth per game")
    console.print(f"\nThen run: pgnc build {output_path}")
