"""Core build logic for PGN curation."""

import os
from typing import Dict, List, Tuple
from rich.console import Console
from rich.table import Table

from .models import Config, ColorConfig, Game
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
        self.input_variations = 0
        self.input_avg_depth = 0.0
        self.input_size = 0

        # Per-color stats
        self.color_stats = {}  # color -> ColorBuildStats

        # Combined output stats
        self.total_output_games = 0
        self.total_output_variations = 0
        self.total_output_size = 0


class ColorBuildStats:
    """Statistics for a single color build."""

    def __init__(self, color: str):
        self.color = color
        self.output_games = 0
        self.output_variations = 0
        self.output_avg_depth = 0.0
        self.output_size = 0
        self.output_files = []  # List of output filenames
        self.game_stats = []  # List of (game_index, game_name, variations_before, variations_after)


def build(config: Config, dry_run: bool = False, verbose: bool = False, depth: int = 10, split: bool = False) -> BuildStats:
    """
    Execute the build process based on configuration.

    Args:
        config: Validated configuration object
        dry_run: If True, don't write output file
        verbose: If True, show detailed progress
        depth: Number of move pairs to include (default: 10)
        split: If True, save each game in a separate file

    Returns:
        BuildStats object with build statistics
    """
    stats = BuildStats()

    # Store output prefix
    output_prefix = config.output

    # Read source PGN once (shared across all color configs)
    if verbose:
        console.print(f"[cyan]Reading source PGN:[/cyan] {config.source}")

    source_games = parse_pgn(config.source)
    stats.input_games = len(source_games)
    stats.input_size = os.path.getsize(config.source)

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

    # Process each color configuration
    for color_config in config.configs:
        color_stats = build_color_config(
            color_config,
            source_games,
            output_prefix,
            depth,
            dry_run,
            verbose,
            split
        )

        stats.color_stats[color_config.color] = color_stats
        stats.total_output_games += color_stats.output_games
        stats.total_output_variations += color_stats.output_variations
        stats.total_output_size += color_stats.output_size

    return stats


def build_color_config(
    color_config: ColorConfig,
    source_games: List,
    output_prefix: str,
    depth: int,
    dry_run: bool,
    verbose: bool,
    split: bool
) -> ColorBuildStats:
    """
    Build output for a single color configuration.

    Args:
        color_config: Color-specific configuration
        source_games: Parsed source PGN games
        output_prefix: Output filename prefix
        depth: Number of move pairs
        dry_run: Preview mode
        verbose: Detailed output
        split: Save each game separately

    Returns:
        ColorBuildStats with statistics for this color
    """
    color_stats = ColorBuildStats(color_config.color)

    # Calculate max_depth based on color
    if color_config.color == "white":
        calculated_max_depth = 2 * depth + 1
    else:  # black
        calculated_max_depth = 2 * depth

    if verbose:
        console.print(f"\n[bold cyan]Processing {color_config.color.upper()} repertoire:[/bold cyan]")

    # Expand shorthand syntax into games list if needed
    color_config = expand_shorthand_to_games(color_config, len(source_games))

    # Process games
    output_games = []
    output_game_indices = []  # Track original source game indices (1-based)

    for game_config in color_config.games:
        if game_config.index >= len(source_games):
            if verbose:
                console.print(
                    f"  [yellow]⚠[/yellow] Game index {game_config.index + 1} out of range "
                    f"(only {len(source_games)} games), skipping"
                )
            continue

        source_game = source_games[game_config.index]
        # Use appropriate header based on color
        header_field = "Black" if color_config.color == "black" else "White"
        game_name = game_config.name or source_game.headers.get(
            header_field, f"Game {game_config.index + 1}"
        )

        # Count variations in source game (before any processing)
        source_variations = count_variations(source_game)

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
            output_game_indices.append(game_config.index + 1)  # Store 1-based index
            if verbose:
                console.print(
                    f"  [yellow]⊘[/yellow] Game [{game_config.index + 1}] {game_name}: "
                    "Headers preserved, variations removed"
                )
            # Track stats - all variations removed
            color_stats.game_stats.append((
                game_config.index + 1,
                game_name,
                source_variations,
                0
            ))
            continue

        # Filter variations
        filtered_game = filter_game_variations(source_game, game_config)

        if filtered_game is None:
            continue

        # Apply depth trimming
        # Use per-game override if specified, otherwise use calculated max_depth
        max_depth = game_config.max_depth or calculated_max_depth
        filtered_game = trim_game_depth(filtered_game, max_depth)

        variations_after = count_variations(filtered_game)

        # Skip empty games if configured
        if color_config.settings.remove_empty_games and variations_after == 0:
            if verbose:
                console.print(
                    f"  [yellow]⚠[/yellow] Game [{game_config.index + 1}] {game_name}: "
                    "Removed (no variations after filtering)"
                )
            continue

        output_games.append(filtered_game)
        output_game_indices.append(game_config.index + 1)  # Store 1-based index

        # Track stats for this game (source variations vs final variations)
        color_stats.game_stats.append((
            game_config.index + 1,  # 1-based index
            game_name,
            source_variations,  # Original count from source
            variations_after    # Final count after filtering and trimming
        ))

        # Report
        if verbose:
            remove_count = len(game_config.remove_variations or [])
            add_count = len(game_config.add_variations or [])
            filter_info = ""
            if remove_count > 0:
                filter_info = f", {remove_count} remove filter(s)"
            if add_count > 0:
                filter_info += f", {add_count} add filter(s)" if filter_info else f", {add_count} add filter(s)"

            depth_info = ""
            if max_depth:
                depth_info = f", trimmed to {max_depth} moves"

            console.print(
                f"  [green]✓[/green] Game [{game_config.index + 1}] {game_name}: "
                f"{variations_after} variation(s){filter_info}{depth_info}"
            )

    # Calculate output statistics for this color
    color_stats.output_games = len(output_games)
    for game in output_games:
        color_stats.output_variations += count_variations(game)

    if color_stats.output_variations > 0 and len(output_games) > 0:
        total_depth = sum(get_average_depth(g) for g in output_games if g)
        color_stats.output_avg_depth = total_depth / len(output_games)

    # Write output
    if not dry_run:
        if split:
            # Split mode: write each game to a separate file
            if verbose:
                console.print(f"  [cyan]Writing output (split mode):[/cyan]")

            total_size = 0
            for i, game in enumerate(output_games):
                # Construct filename: {prefix}_{color}_{depth}_{game_index}.pgn
                # game_index is from original source file (1-based)
                original_game_index = output_game_indices[i]
                game_filename = f"{output_prefix}_{color_config.color}_{depth}_{original_game_index}.pgn"
                write_pgn([game], game_filename, color_config.settings.add_curation_comment)
                file_size = os.path.getsize(game_filename)
                total_size += file_size
                color_stats.output_files.append(game_filename)

                if verbose:
                    console.print(f"    [green]✓[/green] {game_filename}")

            color_stats.output_size = total_size
        else:
            # Normal mode: write all games to a single file
            final_output = f"{output_prefix}_{color_config.color}_{depth}.pgn"

            if verbose:
                console.print(f"  [cyan]Writing output:[/cyan] {final_output}")

            write_pgn(output_games, final_output, color_config.settings.add_curation_comment)
            color_stats.output_size = os.path.getsize(final_output)
            color_stats.output_files.append(final_output)

            if verbose:
                console.print(f"  [green]✓[/green] Written successfully")
    else:
        # Dry run mode
        if split:
            if verbose:
                console.print(f"  [yellow][DRY RUN][/yellow] Would write {len(output_games)} files:")
            for i in range(len(output_games)):
                original_game_index = output_game_indices[i]
                game_filename = f"{output_prefix}_{color_config.color}_{depth}_{original_game_index}.pgn"
                color_stats.output_files.append(game_filename)
                if verbose:
                    console.print(f"    - {game_filename}")
        else:
            final_output = f"{output_prefix}_{color_config.color}_{depth}.pgn"
            color_stats.output_files.append(final_output)
            if verbose:
                console.print(f"  [yellow][DRY RUN][/yellow] Would write to: {final_output}")

    return color_stats


def expand_shorthand_to_games(color_config: ColorConfig, total_games: int) -> ColorConfig:
    """
    Expand shorthand 'skip' or 'include' into full games list.
    Merges with existing games list if both are specified.

    Args:
        color_config: ColorConfig with potentially shorthand syntax
        total_games: Total number of games in source PGN

    Returns:
        ColorConfig with expanded games list
    """
    # If only games list exists (no shorthand), it's already converted to 0-based
    if color_config.games and not color_config.skip and not color_config.include:
        return color_config

    # Build index map from existing games list (if any)
    existing_games_map = {}
    if color_config.games:
        for game in color_config.games:
            existing_games_map[game.index] = game  # Already 0-based

    # Generate games list from shorthand
    games_list = []

    if hasattr(color_config, "_use_skip") and color_config._use_skip:
        # Skip mode: include all games EXCEPT those in skip list
        skip_indices = color_config._skip_indices  # 1-based
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

    elif hasattr(color_config, "_use_include") and color_config._use_include:
        # Include mode: skip all games EXCEPT those in include list
        include_indices = color_config._include_indices  # 1-based
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

    color_config.games = games_list
    return color_config


def print_statistics(stats: BuildStats):
    """
    Print build statistics in a nice table format.

    Args:
        stats: BuildStats object
    """
    console.print("\n[bold cyan]Overall Statistics:[/bold cyan]")

    # Input stats table
    table = Table(show_header=True, header_style="bold cyan", title="Input")
    table.add_column("Metric", style="dim")
    table.add_column("Value", justify="right")

    table.add_row("Games", str(stats.input_games))
    table.add_row("Variations", str(stats.input_variations))
    table.add_row("Avg Depth (moves)", f"{stats.input_avg_depth:.1f}")
    table.add_row("File Size", _format_bytes(stats.input_size))

    console.print(table)

    # Per-color stats
    for color, color_stats in stats.color_stats.items():
        console.print(f"\n[bold {color}]{color.upper()} Repertoire:[/bold {color}]")

        table = Table(show_header=True, header_style=f"bold {color}")
        table.add_column("Metric", style="dim")
        table.add_column("Value", justify="right")

        table.add_row("Games", str(color_stats.output_games))
        table.add_row("Variations", str(color_stats.output_variations))
        table.add_row("Avg Depth (moves)", f"{color_stats.output_avg_depth:.1f}")
        table.add_row("File Size", _format_bytes(color_stats.output_size))
        table.add_row("Output Files", str(len(color_stats.output_files)))

        console.print(table)

        # Show per-game details
        if color_stats.game_stats:
            console.print(f"\n  [bold]Per-Game Details:[/bold]")
            game_table = Table(show_header=True, header_style=f"bold {color}")
            game_table.add_column("Game", style="dim")
            game_table.add_column("Name", style="dim")
            game_table.add_column("Before", justify="right")
            game_table.add_column("After", justify="right")
            game_table.add_column("Change", justify="right")

            for game_idx, game_name, var_before, var_after in color_stats.game_stats:
                change = var_after - var_before
                if change < 0:
                    change_str = f"[red]{change} ({(change/var_before)*100:.1f}%)[/red]"
                elif change > 0:
                    change_str = f"[green]+{change} (+{(change/var_before)*100:.1f}%)[/green]"
                else:
                    change_str = "—"

                game_table.add_row(
                    f"[{game_idx}]",
                    game_name,
                    str(var_before),
                    str(var_after),
                    change_str
                )

            console.print(game_table)

        if color_stats.output_files:
            console.print(f"\n  Files: {', '.join(color_stats.output_files)}")

    # Combined totals
    console.print("\n[bold green]Combined Totals:[/bold green]")
    table = Table(show_header=True, header_style="bold green")
    table.add_column("Metric", style="dim")
    table.add_column("Value", justify="right")

    table.add_row("Total Output Games", str(stats.total_output_games))
    table.add_row("Total Output Variations", str(stats.total_output_variations))
    table.add_row("Total Output Size", _format_bytes(stats.total_output_size))

    console.print(table)


def _format_bytes(size: int) -> str:
    """Format byte size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f}{unit}"
        size /= 1024.0
    return f"{size:.1f}TB"
