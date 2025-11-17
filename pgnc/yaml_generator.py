"""YAML generation for replication configurations."""

import yaml
from pathlib import Path
from typing import List

from .comparator import ComparisonResult


def generate_replication_yaml(
    comparisons: List[ComparisonResult],
    output_path: str,
    pgn1_path: str,
    color: str,
    depth: int
) -> str:
    """
    Generate a replication YAML config from comparison results.

    Args:
        comparisons: List of ComparisonResult objects
        output_path: Path for output YAML file
        pgn1_path: Path to the source/base PGN file (pgn1)
        color: Repertoire color ("white" or "black")
        depth: Number of move pairs

    Returns:
        Path to generated YAML file
    """
    # Build config structure
    config = {
        "name": f"Replication config: {Path(pgn1_path).stem} → target",
        "description": "Auto-generated from pgnc compare - edit as needed",
        "source": pgn1_path,
        "output": f"{Path(pgn1_path).stem}_replicated",
        "configs": []
    }

    # Build games list for the color
    games_list = []

    for comparison in comparisons:
        game_entry = {
            "index": comparison.game1_index,
            "action": "include",
            "name": comparison.game1_name
        }

        # Add remove_variations if there are removed variations
        if comparison.removed_variations:
            game_entry["remove_variations"] = [
                {"moves": moves} for moves in comparison.removed_variations
            ]

        # Add add_variations if there are added variations
        if comparison.added_variations:
            game_entry["add_variations"] = [
                {"moves": moves} for moves in comparison.added_variations
            ]

        games_list.append(game_entry)

    # Create color config
    color_config = {
        "color": color,
        "settings": {
            "preserve_comments": True,
            "add_curation_comment": True
        },
        "games": games_list
    }

    config["configs"].append(color_config)

    # Write YAML with custom formatting
    yaml_content = _format_yaml_with_comments(config, comparisons)

    with open(output_path, "w") as f:
        f.write(yaml_content)

    return output_path


def _format_yaml_with_comments(
    config: dict,
    comparisons: List[ComparisonResult]
) -> str:
    """
    Format YAML with diff comments.

    Args:
        config: Configuration dictionary
        comparisons: List of comparison results

    Returns:
        Formatted YAML string with diff statistics as comments
    """
    # Build YAML with diff comments
    lines = []

    # Header
    lines.append(f"# {config['name']}")
    lines.append(f"# {config['description']}")
    lines.append("")

    lines.append(f"name: \"{config['name']}\"")
    lines.append(f"description: \"{config['description']}\"")
    lines.append(f"source: {config['source']}")
    lines.append(f"output: {config['output']}")
    lines.append("")
    lines.append("configs:")

    for color_config in config["configs"]:
        lines.append(f"  - color: {color_config['color']}")
        lines.append("    settings:")
        for key, value in color_config["settings"].items():
            lines.append(f"      {key}: {str(value).lower()}")
        lines.append("    games:")

        # Add games with diff comments
        for i, game in enumerate(color_config["games"]):
            comparison = comparisons[i]

            lines.append("")
            # Add diff statistics as comment
            lines.append(f"      # Game [{game['index']}]: {game['name']}")
            lines.append(
                f"      # Variations: {comparison.total_variations_game1} → {comparison.total_variations_game2}"
            )
            if comparison.removed_variations:
                lines.append(f"      # Removed: {len(comparison.removed_variations)}")
            if comparison.added_variations:
                lines.append(f"      # Added: {len(comparison.added_variations)}")

            # Game entry
            lines.append(f"      - index: {game['index']}")
            lines.append(f"        action: \"{game['action']}\"")
            lines.append(f"        name: \"{game['name']}\"")

            # Remove variations
            if "remove_variations" in game:
                lines.append("        remove_variations:")
                for var in game["remove_variations"]:
                    lines.append(f"          - moves: \"{var['moves']}\"")

            # Add variations
            if "add_variations" in game:
                lines.append("        add_variations:")
                for var in game["add_variations"]:
                    lines.append(f"          - moves: \"{var['moves']}\"")

    return "\n".join(lines) + "\n"
