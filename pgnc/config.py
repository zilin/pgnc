"""Configuration loading and validation."""

import yaml
from pathlib import Path
from typing import Dict, Any, List
from pydantic import ValidationError

from .models import Config, ColorConfig, Game
from .utils import parse_range_string


def load_config(config_path: str) -> Config:
    """
    Load and validate configuration from YAML file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        Validated Config object

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML syntax is invalid
        ValidationError: If config validation fails
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # Load YAML
    with open(config_file, "r") as f:
        try:
            config_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax in {config_path}:\n{e}")

    if config_data is None:
        raise ValueError(f"Config file is empty: {config_path}")

    # Validate with Pydantic
    try:
        config = Config(**config_data)
    except ValidationError as e:
        raise ValueError(
            f"Config validation failed for {config_path}:\n{format_validation_error(e)}"
        )

    # Expand shorthand syntax (skip/include) for each color config
    for color_config in config.configs:
        expand_shorthand_for_color(color_config)

    return config


def expand_shorthand_for_color(color_config: ColorConfig) -> None:
    """
    Expand shorthand 'skip' or 'include' fields into full games list for a color config.
    Can be mixed with detailed games list for per-game control.
    Modifies the color_config in place.

    Args:
        color_config: ColorConfig object (may have skip/include fields)
    """
    # Convert games list to 0-based if it exists
    if color_config.games:
        for game in color_config.games:
            game.index = game.index - 1  # Convert to 0-based

    # If only games list (no shorthand), we're done
    if color_config.games and not color_config.skip and not color_config.include:
        return

    # Parse shorthand ranges and store for later expansion
    if color_config.skip:
        try:
            skip_indices = parse_range_string(color_config.skip)
            # Store as metadata for later expansion (keep as 1-based for now)
            color_config._skip_indices = skip_indices
            color_config._use_skip = True
        except ValueError as e:
            raise ValueError(f"Color '{color_config.color}': Invalid 'skip' syntax: {e}")

    if color_config.include:
        try:
            include_indices = parse_range_string(color_config.include)
            # Store as metadata for later expansion (keep as 1-based for now)
            color_config._include_indices = include_indices
            color_config._use_include = True
        except ValueError as e:
            raise ValueError(f"Color '{color_config.color}': Invalid 'include' syntax: {e}")


def format_validation_error(error: ValidationError) -> str:
    """
    Format Pydantic validation error for human-readable output.

    Args:
        error: Pydantic ValidationError

    Returns:
        Formatted error message
    """
    lines = []
    for err in error.errors():
        location = " -> ".join(str(loc) for loc in err["loc"])
        message = err["msg"]
        lines.append(f"  {location}: {message}")

    return "\n".join(lines)


def validate_config_file(config_path: str) -> tuple[bool, str]:
    """
    Validate config file and return success status with message.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        Tuple of (is_valid, message)
    """
    try:
        config = load_config(config_path)

        messages = [
            "✓ Config syntax valid",
            f"✓ Source file exists: {config.source}",
            f"✓ Output prefix: {config.output}",
            f"✓ {len(config.configs)} color configuration(s)",
        ]

        # Show details for each color config
        for color_config in config.configs:
            messages.append(f"\n  [{color_config.color.upper()}]")

            # Show game selection method
            if color_config.skip:
                messages.append(f"  ✓ Using 'skip' shorthand: {color_config.skip}")
            elif color_config.include:
                messages.append(f"  ✓ Using 'include' shorthand: {color_config.include}")

            if color_config.games:
                messages.append(f"  ✓ {len(color_config.games)} game(s) with detailed config")

            # Count filters (only if games list exists)
            skip_count = 0
            keep_count = 0
            if color_config.games:
                skip_count = sum(len(g.skip_variations or []) for g in color_config.games)
                keep_count = sum(len(g.keep_variations or []) for g in color_config.games)

            if skip_count > 0:
                messages.append(f"  ✓ {skip_count} variation skip filter(s) defined")
            if keep_count > 0:
                messages.append(f"  ✓ {keep_count} variation keep filter(s) defined")

            if color_config.plan_comments:
                messages.append(f"  ✓ {len(color_config.plan_comments)} plan comment(s) to add")

        messages.append("\n✅ Configuration is valid!")

        return True, "\n".join(messages)

    except (FileNotFoundError, ValueError) as e:
        return False, f"❌ Validation failed:\n{str(e)}"
    except Exception as e:
        return False, f"❌ Unexpected error:\n{str(e)}"
