"""Command-line interface for PGN Curator."""

import click
from rich.console import Console

from . import __version__
from .config import load_config, validate_config_file
from .builder import build, print_statistics
from .inspector import inspect_pgn, generate_starter_config
from .lichess import upload_pgn_to_study, save_token, load_token


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


if __name__ == "__main__":
    cli()
