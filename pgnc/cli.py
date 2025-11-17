"""Command-line interface for PGN Curator."""

import click
from rich.console import Console

from . import __version__
from .config import load_config, validate_config_file
from .builder import build, print_statistics
from .inspector import inspect_pgn, generate_starter_config
from .lichess import upload_pgn_to_study, save_token, load_token
from .comparator import compare_pgn_files
from .yaml_generator import generate_replication_yaml


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
@click.option(
    "--depth", "-d", type=int, default=10, help="Number of move pairs to include (default: 10)"
)
@click.option(
    "--split", is_flag=True, help="Save each game in a separate file"
)
def build_cmd(config_file, dry_run, verbose, quiet, stats, output, depth, split):
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
            console.print(f"[cyan]Output prefix:[/cyan] {config.output}")
            console.print(f"[cyan]Depth:[/cyan] {depth} move pairs")
            console.print(f"[cyan]Colors:[/cyan] {', '.join([c.color for c in config.configs])}")

            if dry_run:
                console.print("[yellow][DRY RUN MODE][/yellow]")

        # Execute build
        build_stats = build(config, dry_run=dry_run, verbose=verbose or stats, depth=depth, split=split)

        # Show statistics
        if stats:
            print_statistics(build_stats)

        # Success message
        if not quiet and not dry_run:
            console.print(f"\n[green]✅ Done![/green]")
            console.print(f"\nCreated {build_stats.total_output_games} game(s) in {len(build_stats.color_stats)} color(s):")
            for color, color_stats in build_stats.color_stats.items():
                console.print(f"  [{color}] {color_stats.output_variations} variations, "
                             f"avg depth {color_stats.output_avg_depth:.1f} moves")
                for filename in color_stats.output_files:
                    console.print(f"    - {filename}")

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
    "--list-variations", 
    is_flag=True, 
    help="List all variation move sequences (for specific game if --game is used, or all games)"
)
def inspect(pgn_file, game, list_variations):
    """
    Inspect PGN file structure and statistics.

    Examples:

        pgnc inspect openings_2025.pgn

        pgnc inspect openings_2025.pgn --game 1

        pgnc inspect openings_2025.pgn --list-variations  # List variations for all games

        pgnc inspect openings_2025.pgn --game 1 --list-variations  # List variations for game 1
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


@cli.command()
@click.argument("pgn_file", type=click.Path(exists=True))
@click.option(
    "--name", "-n", help="Study name (default: PGN filename)"
)
@click.option(
    "--private",
    is_flag=True,
    help="Make study private (default: public)"
)
@click.option(
    "--token",
    help="Lichess API token (default: load from ~/.pgnc/lichess_token). "
         "Get your token from https://lichess.org/account/oauth/token/create"
)
@click.option(
    "--study-id",
    required=True,
    help="Existing study ID (REQUIRED - create study manually on lichess.org first). "
         "Get this from your study URL (e.g., 'ABC123' from https://lichess.org/study/ABC123)"
)
def upload(pgn_file, name, private, token, study_id):
    """
    Upload PGN file to Lichess as a study.

    Each game in the PGN file will become a chapter in the study.
    
    Authentication: Uses personal API token by default (simpler). Get your token from:
    https://lichess.org/account/oauth/token/create
    
    IMPORTANT: Lichess API requires study to exist (create manually first).
    Use --study-id with an existing study ID from lichess.org.

    Examples:

        # Upload PGN games as chapters to existing study
        pgnc upload my_repertoire.pgn --study-id ABC123

        pgnc upload my_repertoire.pgn --study-id ABC123 --token YOUR_TOKEN
    """
    try:
        visibility = "private" if private else "public"
        
        # Validate study_id is provided
        if not study_id:
            console.print("[red]✗ Error: --study-id is required[/red]")
            console.print("\n[cyan]How to get a study ID:[/cyan]")
            console.print("1. Create a study manually on https://lichess.org/study")
            console.print("2. Get the ID from the URL (e.g., 'ABC123' from https://lichess.org/study/ABC123)\n")
            raise click.Abort()
        
        # Handle authentication
        api_token = token
        if not api_token:
            api_token = load_token()
        
        if not api_token:
            console.print("\n[cyan]Personal API token required[/cyan]")
            console.print("\nGet your token from:")
            console.print("[cyan]https://lichess.org/account/oauth/token/create[/cyan]\n")
            console.print("Then either:")
            console.print("  1. Use --token YOUR_TOKEN option")
            console.print("  2. Save to ~/.pgnc/lichess_token file\n")
            provided_token = Prompt.ask("Enter your Lichess API token", default="")
            if not provided_token:
                console.print("[red]✗ No token provided. Aborting.[/red]")
                raise click.Abort()
            api_token = provided_token
            save_token(api_token)
        
        # Upload
        result = upload_pgn_to_study(
            pgn_file,
            study_name=name,
            api_token=api_token,
            visibility=visibility,
            study_id=study_id,
        )
        
        console.print(f"\n[green]✅ Upload complete![/green]")
        console.print(f"Study: [cyan]{result['study_url']}[/cyan]")
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise click.Abort()


@cli.command()
@click.argument("pgn1", type=click.Path(exists=True))
@click.argument("pgn2", type=click.Path(exists=True))
@click.option("--game1", type=int, help="Specific game index in first PGN (1-based)")
@click.option("--game2", type=int, help="Specific game index in second PGN (1-based)")
@click.option("--output", "-o", type=click.Path(), help="Output YAML path")
@click.option(
    "--color",
    type=click.Choice(["white", "black"]),
    required=True,
    help="Repertoire color (required for depth calculation)"
)
@click.option(
    "--depth",
    "-d",
    type=int,
    default=10,
    help="Number of move pairs to compare (default: 10)"
)
def compare(pgn1, pgn2, game1, game2, output, color, depth):
    """
    Compare two PGN files and generate replication YAML.

    Analyzes differences between games and outputs a YAML config
    compatible with 'pgnc build' that can replicate the changes.

    Default behavior (no --game1/--game2):
      Compares all games by index (game 1 vs 1, 2 vs 2, etc.)
      Only outputs games with differences

    Specific game comparison:
      Use --game1 and --game2 to compare specific games

    Examples:

        # Compare all games, output differences for white repertoire
        pgnc compare old.pgn new.pgn --color white

        # Compare specific games with depth limit
        pgnc compare old.pgn new.pgn --game1 1 --game2 1 --color black --depth 15
    """
    try:
        from pathlib import Path

        # Validate game index constraints
        if (game1 is not None and game2 is None) or (game1 is None and game2 is not None):
            console.print("[red]Error:[/red] Both --game1 and --game2 must be specified together")
            raise click.Abort()

        # Default output path
        if output is None:
            pgn1_stem = Path(pgn1).stem
            pgn2_stem = Path(pgn2).stem
            output = f"{pgn1_stem}_to_{pgn2_stem}_replication.yaml"

        # Show comparison info
        console.print(f"\n[cyan]Comparing PGN files:[/cyan]")
        console.print(f"  Baseline: {pgn1}")
        console.print(f"  Target:   {pgn2}")
        console.print(f"  Color:    {color}")
        console.print(f"  Depth:    {depth} move pairs")

        if game1 is not None and game2 is not None:
            console.print(f"  Mode:     Specific games (game {game1} vs game {game2})")
        else:
            console.print(f"  Mode:     All games by index")

        console.print()

        # Perform comparison
        comparisons = compare_pgn_files(
            pgn1,
            pgn2,
            game1_idx=game1,
            game2_idx=game2,
            color=color,
            depth=depth
        )

        if not comparisons:
            console.print("[green]✓[/green] No differences found between the games!")
            return

        # Show summary
        console.print(f"[bold]Found differences in {len(comparisons)} game(s):[/bold]\n")

        for comparison in comparisons:
            console.print(f"  [cyan]Game [{comparison.game2_index}]:[/cyan] {comparison.game2_name}")
            console.print(
                f"    Variations: {comparison.total_variations_game1} → "
                f"{comparison.total_variations_game2}"
            )

            if comparison.removed_variations:
                console.print(f"    [red]Removed:[/red] {len(comparison.removed_variations)}")
            if comparison.added_variations:
                console.print(f"    [green]Added:[/green] {len(comparison.added_variations)}")

            console.print()

        # Generate YAML
        console.print(f"[cyan]Generating replication YAML:[/cyan] {output}")

        generate_replication_yaml(
            comparisons,
            output,
            pgn1,  # Use pgn1 as source (the base to be transformed)
            color,
            depth
        )

        console.print(f"\n[green]✅ Replication config generated:[/green] {output}")
        console.print(f"\nApply changes with: [cyan]pgnc build {output} --depth {depth}[/cyan]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise click.Abort()


if __name__ == "__main__":
    cli()
