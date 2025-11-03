"""Utility functions for PGN Curator."""

from typing import List, Set


def parse_range_string(range_str: str) -> Set[int]:
    """
    Parse range string like "1,3,5-10,20" into set of integers.

    Supports:
    - Individual numbers: "1,3,5"
    - Ranges: "5-10" (inclusive)
    - Mixed: "1,3,5-10,20"

    Args:
        range_str: Range string to parse

    Returns:
        Set of integers

    Raises:
        ValueError: If syntax is invalid

    Examples:
        >>> parse_range_string("1,3,5")
        {1, 3, 5}

        >>> parse_range_string("1-5")
        {1, 2, 3, 4, 5}

        >>> parse_range_string("1,3,5-7,10")
        {1, 3, 5, 6, 7, 10}
    """
    result = set()

    if not range_str.strip():
        return result

    # Split by comma
    parts = range_str.split(",")

    for part in parts:
        part = part.strip()

        if "-" in part:
            # Range like "5-10"
            range_parts = part.split("-")
            if len(range_parts) != 2:
                raise ValueError(
                    f"Invalid range syntax: '{part}'. Expected format: 'start-end'"
                )

            try:
                start = int(range_parts[0].strip())
                end = int(range_parts[1].strip())
            except ValueError:
                raise ValueError(
                    f"Invalid range syntax: '{part}'. Start and end must be integers"
                )

            if start > end:
                raise ValueError(f"Invalid range: {start}-{end}. Start must be <= end")

            result.update(range(start, end + 1))
        else:
            # Single number
            try:
                num = int(part)
                result.add(num)
            except ValueError:
                raise ValueError(f"Invalid number: '{part}'")

    return result


def expand_game_indices(
    games_config: List, total_games: int, one_based: bool = True
) -> dict:
    """
    Expand game configuration into a mapping of index -> action.

    Args:
        games_config: List of game configuration dicts
        total_games: Total number of games in source PGN
        one_based: If True, treat indices as 1-based (convert to 0-based internally)

    Returns:
        Dictionary mapping 0-based index -> game config dict
    """
    index_to_config = {}

    for game_cfg in games_config:
        if isinstance(game_cfg, dict) and "index" in game_cfg:
            # Individual game
            idx = game_cfg["index"]
            if one_based:
                idx = idx - 1  # Convert to 0-based

            if idx < 0 or idx >= total_games:
                raise ValueError(
                    f"Game index {game_cfg['index']} out of range (1-{total_games})"
                )

            index_to_config[idx] = game_cfg

    return index_to_config
