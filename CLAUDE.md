# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PGN Curator is a Python command-line tool for curating chess opening repertoires. It transforms large PGN (Portable Game Notation) files into focused, student-specific training materials using declarative YAML configurations. The tool implements a "Layered Depth Learning" approach where students progressively learn opening theory in stages (Layer 1: 12-14 moves, Layer 2: 15-20 moves, Layer 3: 20+ moves).

## Installation and Setup

```bash
# Install in editable mode
pip install -e .

# Install dependencies
pip install -r requirements.txt
```

## Common Commands

### Development Workflow
```bash
# Run the CLI (after installation)
pgnc --help

# Inspect a PGN file
pgnc inspect <file.pgn>
pgnc inspect <file.pgn> --game 1
pgnc inspect <file.pgn> --list-variations

# Build from config
pgnc build <config.yaml>
pgnc build <config.yaml> --depth 10  # Specify move pairs (default: 10)
pgnc build <config.yaml> --split     # Save each game in separate files
pgnc build <config.yaml> --dry-run --stats

# Validate config
pgnc validate <config.yaml>

# Generate starter config
pgnc init <file.pgn> -o config.yaml

# Upload to Lichess
pgnc upload <file.pgn> --study-id ABC123
```

### Testing
There are currently no automated tests in the project.

## Architecture

### Entry Point
- **pgnc/cli.py**: Click-based CLI with commands: `build`, `validate`, `inspect`, `init`, `upload`
- Entry point defined in setup.py: `pgnc=pgnc.cli:cli`

### Core Processing Pipeline
1. **Config Loading** (pgnc/config.py):
   - Load YAML config with Pydantic validation
   - Expand shorthand syntax (`skip: "1,3-5"` or `include: "1,2"`) into full game list
   - Convert 1-based indexing (user-facing) to 0-based (internal)

2. **Build Initialization** (pgnc/builder.py):
   - Calculate `max_depth` from `--depth` flag and `color` setting
   - Construct final output filename: `{output_prefix}_{color}_{depth}.pgn`
   - Update config with final output path

3. **PGN Parsing** (pgnc/pgn_processor.py):
   - Uses python-chess library to parse PGN files
   - Parse move sequences in SAN notation
   - Pattern matching for variation filtering

4. **Game Filtering** (pgnc/builder.py + pgnc/pgn_processor.py):
   - Process each game according to its action: `include`, `skip`, or `skip_keep_headers`
   - Apply variation filters (whitelist via `keep_variations` or blacklist via `skip_variations`)
   - Trim variations to max_depth (in half-moves/plies)
   - Preserve comments, annotations, and NAGs from original PGN

5. **Output** (pgnc/pgn_processor.py):
   - Write curated games to PGN file(s) with constructed filename(s)
   - In normal mode: single file `{prefix}_{color}_{depth}.pgn`
   - In split mode (`--split`): separate files `{prefix}_{color}_{depth}_{game_index}.pgn`
   - Add curation metadata header
   - Generate statistics (variations, depth, file size)

### Data Models (pgnc/models.py)
- **Config**: Top-level configuration with source/output paths and list of ColorConfig
- **ColorConfig**: Color-specific configuration (color, settings, games, include/skip, etc.)
- **Settings**: Per-color curation settings (preserve_comments, etc. - no color field)
- **Game**: Per-game configuration (index, action, filters, max_depth override)
- **VariationFilter**: Filter definition with move sequence, reason, and optional depth constraint
- **PlanComment**: Add/override comments at specific variation endpoints
- **Importance**: Tag variations by importance level (planned feature)

### Key Concepts

**Depth Calculation**:
- The `--depth` CLI flag specifies the number of move pairs (default: 10)
- Depth is converted to half-moves (plies) based on the repertoire color from config:
  - **White repertoire**: `max_depth = 2 * depth + 1` (e.g., depth=10 → 21 half-moves)
  - **Black repertoire**: `max_depth = 2 * depth` (e.g., depth=10 → 20 half-moves)
- Per-game `max_depth` in config can override the calculated value (specified in half-moves)
- Calculation happens in `builder.build()` at the start of the build process

**Multi-Color Support**:
- A single YAML file can contain multiple color configurations
- Each color config is independent with its own game selection and settings
- Build process loops through each color config and generates separate output files
- Useful for managing both white and black repertoires in one place

**1-based vs 0-based Indexing**:
- User-facing config files use 1-based indexing (Game [1], [2], [3]...)
- Internal processing converts to 0-based for Python list access
- Conversion happens in `config.expand_shorthand_for_color()` and `builder.expand_shorthand_to_games()`

**Variation Filtering**:
- **Whitelist approach** (`keep_variations`): Only keep variations matching specified move sequences
- **Blacklist approach** (`skip_variations`): Skip variations matching specified move sequences
- Cannot mix both approaches in same game
- Filters match by move sequence prefix (e.g., "1.e4 c5" matches all Sicilian lines)

**Shorthand Syntax**:
- `include: "1,3,5-10"` - Include only these games, skip all others
- `skip: "2,4"` - Skip these games, include all others
- Cannot use both `skip` and `include` together
- Can mix shorthand with detailed `games` list - detailed config overrides shorthand

**Depth Trimming**:
- Depth trimming always works with half-moves (plies)
- The calculated `max_depth` is derived from the `--depth` flag and config `color` setting
- Per-game `max_depth` override in config bypasses the calculation (must specify in half-moves)
- Trims all variations at specified depth while preserving comments

## File Structure

```
pgnc/
├── __init__.py         # Version info
├── cli.py              # Click CLI commands
├── config.py           # Config loading and validation
├── models.py           # Pydantic data models
├── builder.py          # Main build orchestration and stats
├── pgn_processor.py    # PGN parsing, filtering, trimming, writing
├── inspector.py        # PGN inspection and analysis
├── lichess.py          # Lichess API integration
└── utils.py            # Range parsing utilities

examples/
├── simple.yaml         # Simple config example
└── comprehensive.yaml  # Full-featured config example
```

## Configuration Format

Config files are YAML with Pydantic validation. Key fields:
- `name`, `source`: Required metadata
- `output`: Output filename prefix (final filename will be `{output}_{color}_{depth}.pgn`)
- `configs`: List of color-specific configurations (at least one required)
  - Each config has:
    - `color`: "white" or "black" (required)
    - `settings`: Per-color settings (preserve_comments, etc.)
    - `include`/`skip`: Shorthand game selection (mutually exclusive)
    - `games`: Detailed per-game configuration (can include per-game `max_depth` override in half-moves)
    - `plan_comments`: (Optional) Add comments at variation endpoints
    - `importance`: (Optional) Tag variation importance levels

**Important**:
- Can have both white and black configurations in a single YAML file
- Each color config has its own `include`/`skip` game selection
- Each color can have different settings
- The `output` field is a prefix; the final filename(s) depend on mode:
  - **Normal mode**: `{output}_{color}_{depth}.pgn`
    - Example: `output: my_repertoire` with `color: white` and `--depth 10` produces `my_repertoire_white_10.pgn`
  - **Split mode** (`--split` flag): `{output}_{color}_{depth}_{game_index}.pgn` (one file per game)
    - Example: `my_repertoire_white_10_2.pgn` (original game index 2)

See `examples/` directory for working examples.

## Lichess Integration (pgnc/lichess.py)

Uploads PGN files to Lichess studies:
- Requires personal API token with `study:write` scope
- Study must exist (create manually on lichess.org first)
- Each game in PGN becomes a chapter in the study
- Token stored in `~/.pgnc/lichess_token` or passed via `--token` flag

## Dependencies

- **chess>=1.10.0**: PGN parsing and move validation
- **click>=8.1.0**: CLI framework
- **pyyaml>=6.0**: YAML parsing
- **pydantic>=2.0.0**: Config validation with BaseModel
- **rich>=13.0.0**: Terminal UI (Console, Table)
- **requests>=2.31.0**: HTTP for Lichess API
