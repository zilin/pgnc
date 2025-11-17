"""Pydantic models for configuration validation."""

import os
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


class VariationFilter(BaseModel):
    """Filter for skipping or keeping specific variations."""

    moves: str = Field(..., description="Move sequence in SAN notation")
    reason: Optional[str] = Field(None, description="Reason for filtering")
    depth: Optional[int] = Field(
        None, description="Only apply if variation exceeds this depth"
    )

    @field_validator("moves")
    @classmethod
    def validate_moves_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Move sequence cannot be empty")
        return v.strip()


class Game(BaseModel):
    """Configuration for a single game in the source PGN."""

    index: int = Field(..., ge=1, description="1-based game index in source PGN")
    action: Literal["include", "skip", "skip_keep_headers"] = Field(
        ..., description="What to do with this game"
    )
    name: Optional[str] = Field(None, description="Optional name for documentation")
    remove_variations: Optional[List[VariationFilter]] = Field(
        None, description="Variations to remove from source"
    )
    add_variations: Optional[List[VariationFilter]] = Field(
        None, description="Variations to add (result = (all - removed) ∪ added)"
    )
    max_depth: Optional[int] = Field(
        None, ge=1, description="Override calculated max_depth for this game (in half-moves)"
    )
    min_depth: Optional[int] = Field(None, ge=0, description="Minimum variation depth")


class Settings(BaseModel):
    """Per-color settings for curation."""

    min_depth: int = Field(0, ge=0, description="Minimum moves to keep variation")
    preserve_comments: bool = Field(
        True, description="Preserve all annotations and comments"
    )
    preserve_headers: bool = Field(True, description="Preserve PGN headers")
    add_curation_comment: bool = Field(
        True, description="Add metadata about curation process"
    )
    remove_empty_games: bool = Field(
        False, description="Remove games with no variations after filtering"
    )


class PlanComment(BaseModel):
    """Plan comment to add or override at variation endpoint."""

    variation: str = Field(..., description="Move sequence to identify variation")
    at_move: Optional[int] = Field(
        None, ge=1, description="Move number to add comment (default: end)"
    )
    comment: str = Field(..., description="The plan comment text")
    replace: bool = Field(False, description="Replace existing comment or append")


class Importance(BaseModel):
    """Tag variations by importance level."""

    main_lines: Optional[List[str]] = Field(
        None, description="Main line move sequences"
    )
    important: Optional[List[str]] = Field(
        None, description="Important but not main lines"
    )
    sidelines: Optional[List[str]] = Field(None, description="Sideline move sequences")
    rare: Optional[List[str]] = Field(None, description="Rare/optional move sequences")


class ColorConfig(BaseModel):
    """Configuration for a specific color repertoire."""

    color: Literal["white", "black"] = Field(
        ..., description="Repertoire color (white or black)"
    )
    settings: Settings = Field(
        default_factory=Settings, description="Settings for this color"
    )
    games: Optional[List[Game]] = Field(
        None, description="Game selection and filtering (detailed)"
    )
    skip: Optional[str] = Field(
        None,
        description="Shorthand to skip games by range (e.g., '1,3,5-10,20'). "
        "Games not listed here are included.",
    )
    include: Optional[str] = Field(
        None,
        description="Shorthand to include games by range (e.g., '8,27'). "
        "Games not listed here are skipped.",
    )
    importance: Optional[Importance] = Field(
        None, description="Importance tagging for variations"
    )
    plan_comments: Optional[List[PlanComment]] = Field(
        None, description="Plan comments to add/override"
    )

    @model_validator(mode="after")
    def validate_game_specification(self):
        """Validate game specification and mutual exclusions."""
        # Must specify either games, skip, or include
        if not self.games and not self.skip and not self.include:
            raise ValueError(
                f"Color '{self.color}': Must specify at least one of: 'games', 'skip', or 'include'"
            )

        # Cannot use both skip and include shorthand
        if self.skip and self.include:
            raise ValueError(
                f"Color '{self.color}': Cannot specify both 'skip' and 'include' shorthand. Use one or the other."
            )

        # CAN mix games list with shorthand (for detailed control on specific games)
        # The games list will override the shorthand for those specific indices

        return self


class Config(BaseModel):
    """Complete configuration for PGN curation."""

    name: str = Field(..., description="Configuration name")
    version: Optional[str] = Field(None, description="Version for tracking")
    created: Optional[str] = Field(None, description="Creation date")
    description: Optional[str] = Field(
        None, description="Description of this configuration"
    )
    source: str = Field(..., description="Source PGN file path")
    output: str = Field(..., description="Output file prefix")
    configs: List[ColorConfig] = Field(
        ..., description="Color-specific configurations (at least one required)"
    )

    @field_validator("source")
    @classmethod
    def validate_source_exists(cls, v: str) -> str:
        if not os.path.exists(v):
            raise ValueError(f"Source file not found: {v}")
        if not v.endswith(".pgn"):
            raise ValueError(f"Source file must be a PGN file: {v}")
        return v

    @field_validator("output")
    @classmethod
    def validate_output_path(cls, v: str) -> str:
        # Output is now a prefix, not a full filename
        # The final filename will be constructed as {prefix}_{color}_{depth}.pgn
        # Check if output directory exists (if a path is provided)
        output_dir = os.path.dirname(v)
        if output_dir and not os.path.exists(output_dir):
            raise ValueError(f"Output directory does not exist: {output_dir}")
        return v

    @model_validator(mode="after")
    def validate_configs_not_empty(self):
        """Ensure at least one color config exists."""
        if not self.configs or len(self.configs) == 0:
            raise ValueError("Must specify at least one color configuration in 'configs'")

        # Check for duplicate colors
        colors = [c.color for c in self.configs]
        if len(colors) != len(set(colors)):
            raise ValueError("Cannot have duplicate color configurations")

        return self

