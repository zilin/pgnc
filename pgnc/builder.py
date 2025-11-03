"""Core build logic for PGN curation."""

import os
from typing import Dict, List, Tuple
from rich.console import Console
from rich.table import Table

from .models import Config, Game
from .pgn_processor import (
    parse_pgn,
    filter_game_variations,
    trim_game_depth,
    count_variations,
    get_average_depth,
    write_pgn,
)


console = Console()


class BuildStats:
    """Statistics for build process."""

    def __init__(self):
        self.input_games = 0
        self.output_games = 0
        self.input_variations = 0
        self.output_variations = 0
        self.input_avg_depth = 0.0
        self.output_avg_depth = 0.0
        self.input_size = 0
        self.output_size = 0


def build(config: Config, dry_run: bool = False, verbose: bool = False) -> BuildStats:
    """
    Execute the build process based on configuration.

    Args:
        config: Validated configuration object
        dry_run: If True, don't write output file
        verbose: If True, show detailed progress

    Returns:
        BuildStats object with build statistics
    """
    stats = BuildStats()

    # Read source PGN
    if verbose:
        console.print(f"[cyan]Reading source PGN:[/cyan] {config.source}")

    source_games = parse_pgn(config.source)
    stats.input_games = len(source_games)
    stats.input_size = os.path.getsize(config.source)

    # Expand shorthand syntax into games list if needed
    config = expand_shorthand_to_games(config, len(source_games))

    # Calculate input statistics
    for game in source_games:
        stats.input_variations += count_variations(game)

    if stats.input_variations > 0:
        total_depth = sum(get_average_depth(g) for g in source_games)
        stats.input_avg_depth = total_depth / len(source_games)

    if verbose:
        console.print(
            f"[green]✓[/green] Loaded {stats.input_games} game(s), "
            f"{stats.input_variations} variations"
        )

    # Process games
    if verbose:
        console.print("\n[cyan]Processing games...[/cyan]")

    output_games = []

    for game_config in config.games:
        if game_config.index >= len(source_games):
            console.print(
                f"[yellow]⚠[/yellow] Game index {game_config.index + 1} out of range "
                f"(only {len(source_games)} games), skipping"
            )
            continue

        source_game = source_games[game_config.index]
        game_name = game_config.name or source_game.headers.get(
            "White", f"Game {game_config.index + 1}"
        )

        # Process based on action
        if game_config.action == "skip":
            if verbose:
                console.print(
                    f"  [red]✗[/red] Game [{game_config.index + 1}] {game_name}: Skipped completely"
                )
            continue

        if game_config.action == "skip_keep_headers":
            filtered_game = filter_game_variations(source_game, game_config)
            output_games.append(filtered_game)
            if verbose:
                console.print(
                    f"  [yellow]⊘[/yellow] Game [{game_config.index + 1}] {game_name}: "
                    "Headers preserved, variations removed"
                )
            continue

        # Filter variations
        filtered_game = filter_game_variations(source_game, game_config)

        if filtered_game is None:
            continue

        # Count variations before trimming
        variations_before = count_variations(filtered_game)

        # Apply depth trimming
        max_depth = game_config.max_depth or config.settings.max_depth
        if max_depth:
            filtered_game = trim_game_depth(filtered_game, max_depth)

        variations_after = count_variations(filtered_game)

        # Skip empty games if configured
        if config.settings.remove_empty_games and variations_after == 0:
            if verbose:
                console.print(
                    f"  [yellow]⚠[/yellow] Game [{game_config.index + 1}] {game_name}: "
                    "Removed (no variations after filtering)"
                )
            continue

        output_games.append(filtered_game)

        # Report
        if verbose:
            skip_count = len(game_config.skip_variations or [])
            keep_count = len(game_config.keep_variations or [])
            filter_info = ""
            if skip_count > 0:
                filter_info = f", {skip_count} skip filter(s)"
            elif keep_count > 0:
                filter_info = f", {keep_count} keep filter(s)"

            depth_info = ""
            if max_depth:
                depth_info = f", trimmed to {max_depth} moves"

            console.print(
                f"  [green]✓[/green] Game [{game_config.index + 1}] {game_name}: "
                f"{variations_after} variation(s){filter_info}{depth_info}"
            )

    # Calculate output statistics
    stats.output_games = len(output_games)
    for game in output_games:
        stats.output_variations += count_variations(game)

    if stats.output_variations > 0 and len(output_games) > 0:
        total_depth = sum(get_average_depth(g) for g in output_games if g)
        stats.output_avg_depth = total_depth / len(output_games)

    # Write output
    if not dry_run:
        if verbose:
            console.print(f"\n[cyan]Writing output:[/cyan] {config.output}")

        write_pgn(output_games, config.output, config.settings.add_curation_comment)
        stats.output_size = os.path.getsize(config.output)

        if verbose:
            console.print(f"[green]✓[/green] Written successfully")
    else:
        console.print(f"\n[yellow][DRY RUN][/yellow] Would write to: {config.output}")
        # Estimate size (rough approximation)
        if stats.input_size > 0:
            size_ratio = stats.output_variations / max(stats.input_variations, 1)
            stats.output_size = int(stats.input_size * size_ratio)

    return stats


def print_statistics(stats: BuildStats):
    """
    Print build statistics in a nice table format.

    Args:
        stats: BuildStats object
    """
    console.print("\n[cyan]Statistics:[/cyan]")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="dim")
    table.add_column("Input", justify="right")
    table.add_column("Output", justify="right")
    table.add_column("Change", justify="right")

    # Games
    table.add_row(
        "Games",
        str(stats.input_games),
        str(stats.output_games),
        _format_change(stats.input_games, stats.output_games),
    )

    # Variations
    table.add_row(
        "Variations",
        str(stats.input_variations),
        str(stats.output_variations),
        _format_change(stats.input_variations, stats.output_variations),
    )

    # Average depth
    table.add_row(
        "Avg Depth (moves)",
        f"{stats.input_avg_depth:.1f}",
        f"{stats.output_avg_depth:.1f}",
        _format_change(stats.input_avg_depth, stats.output_avg_depth, is_float=True),
    )

    # File size
    table.add_row(
        "File Size",
        _format_bytes(stats.input_size),
        _format_bytes(stats.output_size),
        _format_change(stats.input_size, stats.output_size, is_bytes=True),
    )

    console.print(table)


def _format_change(
    before: float, after: float, is_float: bool = False, is_bytes: bool = False
) -> str:
    """Format the change between before and after values."""
    if before == 0:
        return "—"

    diff = after - before
    percent = ((after - before) / before) * 100

    if is_bytes:
        diff_str = _format_bytes(abs(diff))
        if diff < 0:
            return f"[red]-{diff_str} ({percent:.0f}%)[/red]"
        elif diff > 0:
            return f"[green]+{diff_str} (+{percent:.0f}%)[/green]"
        else:
            return "—"

    if is_float:
        if diff < 0:
            return f"[red]{diff:.1f} ({percent:.0f}%)[/red]"
        elif diff > 0:
            return f"[green]+{diff:.1f} (+{percent:.0f}%)[/green]"
        else:
            return "—"

    # Integer
    if diff < 0:
        return f"[red]{diff:+d} ({percent:.0f}%)[/red]"
    elif diff > 0:
        return f"[green]{diff:+d} (+{percent:.0f}%)[/green]"
    else:
        return "—"


def _format_bytes(size: int) -> str:
    """Format byte size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f}{unit}"
        size /= 1024.0
    return f"{size:.1f}TB"


def expand_shorthand_to_games(config: Config, total_games: int) -> Config:
    """
    Expand shorthand 'skip' or 'include' into full games list.
    Merges with existing games list if both are specified.

    Args:
        config: Config with potentially shorthand syntax
        total_games: Total number of games in source PGN

    Returns:
        Config with expanded games list
    """
    # If only games list exists (no shorthand), it's already converted to 0-based
    if config.games and not config.skip and not config.include:
        return config

    # Build index map from existing games list (if any)
    existing_games_map = {}
    if config.games:
        for game in config.games:
            existing_games_map[game.index] = game  # Already 0-based

    # Generate games list from shorthand
    games_list = []

    if hasattr(config, "_use_skip") and config._use_skip:
        # Skip mode: include all games EXCEPT those in skip list
        skip_indices = config._skip_indices  # 1-based
        for i in range(total_games):
            # Check if this game has detailed config
            if i in existing_games_map:
                games_list.append(existing_games_map[i])  # Use detailed config
                continue

            game_num = i + 1  # 1-based for display/config
            if game_num in skip_indices:
                # Create with 1-based, then convert to 0-based
                game = Game(index=game_num, action="skip")
                game.index = i  # Convert to 0-based internally
                games_list.append(game)
            else:
                game = Game(index=game_num, action="include")
                game.index = i  # Convert to 0-based internally
                games_list.append(game)

    elif hasattr(config, "_use_include") and config._use_include:
        # Include mode: skip all games EXCEPT those in include list
        include_indices = config._include_indices  # 1-based
        for i in range(total_games):
            # Check if this game has detailed config
            if i in existing_games_map:
                games_list.append(existing_games_map[i])  # Use detailed config
                continue

            game_num = i + 1  # 1-based for display/config
            if game_num in include_indices:
                game = Game(index=game_num, action="include")
                game.index = i  # Convert to 0-based internally
                games_list.append(game)
            else:
                game = Game(index=game_num, action="skip")
                game.index = i  # Convert to 0-based internally
                games_list.append(game)

    config.games = games_list
    return config
