"""Command-line interface for PGN Curator."""

import click
from rich.console import Console

from . import __version__
from .config import load_config, validate_config_file
from .builder import build, print_statistics
from .inspector import inspect_pgn, generate_starter_config


console = Console()


@click.group()
@click.version_option(version=__version__)
def cli():
    """
    PGN Curator - Config-driven chess opening repertoire curation tool.

    Transform large PGN files into student-specific opening repertoires
    using declarative YAML configuration files.
    """
    pass


@cli.command(name="build")
@click.argument("config_file", type=click.Path(exists=True))
@click.option("--dry-run", "-n", is_flag=True, help="Preview without writing output")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed processing info")
@click.option("--quiet", "-q", is_flag=True, help="Only show errors")
@click.option("--stats", is_flag=True, help="Show detailed statistics")
@click.option(
    "--output", "-o", type=click.Path(), help="Override output path from config"
)
def build_cmd(config_file, dry_run, verbose, quiet, stats, output):
    """
    Build curated PGN from configuration file.

    Examples:

        pgnc build john_config.yaml

        pgnc build john_config.yaml --dry-run

        pgnc build john_config.yaml --verbose --stats
    """
    try:
        # Load config
        config = load_config(config_file)

        # Override output if specified
        if output:
            config.output = output

        # Show config info
        if not quiet:
            console.print(f"\n[cyan]Reading config:[/cyan] {config_file}")
            console.print(f"[cyan]Source PGN:[/cyan] {config.source}")
            console.print(f"[cyan]Output PGN:[/cyan] {config.output}")

            if dry_run:
                console.print("[yellow][DRY RUN MODE][/yellow]")

        # Execute build
        build_stats = build(config, dry_run=dry_run, verbose=verbose or stats)

        # Show statistics
        if stats or verbose:
            print_statistics(build_stats)

        # Success message
        if not quiet and not dry_run:
            console.print(f"\n[green]✅ Done![/green]")
            console.print(f"\nCreated: {config.output}")
            console.print(
                f"  {build_stats.output_variations} variations, "
                f"avg depth {build_stats.output_avg_depth:.1f} moves"
            )

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise click.Abort()


@cli.command()
@click.argument("config_file", type=click.Path(exists=True))
def validate(config_file):
    """
    Validate configuration file.

    Checks:
    - YAML syntax
    - Required fields
    - File paths exist
    - Game indices in range
    - Move sequences valid

    Examples:

        pgnc validate john_config.yaml
    """
    console.print(f"\n[cyan]Validating:[/cyan] {config_file}\n")

    is_valid, message = validate_config_file(config_file)

    console.print(message)

    if not is_valid:
        raise click.Abort()


@cli.command()
@click.argument("pgn_file", type=click.Path(exists=True))
@click.option("--game", type=int, help="Show details for specific game index")
@click.option(
    "--list-variations", is_flag=True, help="List all variation move sequences"
)
def inspect(pgn_file, game, list_variations):
    """
    Inspect PGN file structure and statistics.

    Examples:

        pgnc inspect openings_2025.pgn

        pgnc inspect openings_2025.pgn --game 0

        pgnc inspect openings_2025.pgn --game 1 --list-variations
    """
    try:
        inspect_pgn(pgn_file, game_index=game, list_variations=list_variations)
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise click.Abort()


@cli.command()
@click.argument("pgn_file", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output config file path")
def init(pgn_file, output):
    """
    Generate starter configuration from PGN file.

    Creates a basic YAML config with all games set to 'include'.
    Edit the generated file to customize filtering.

    Examples:

        pgnc init openings_2025.pgn

        pgnc init openings_2025.pgn -o my_config.yaml
    """
    try:
        generate_starter_config(pgn_file, output)
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise click.Abort()


if __name__ == "__main__":
    cli()
