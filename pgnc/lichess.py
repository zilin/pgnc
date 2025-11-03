"""Lichess API integration for uploading studies."""

import os
from typing import Optional, Dict
from pathlib import Path

import requests
from rich.console import Console
from rich.prompt import Prompt

from .pgn_processor import parse_pgn

console = Console()

# Lichess API endpoints
LICHESS_API_BASE = "https://lichess.org/api"


class LichessClient:
    """Client for interacting with Lichess API."""

    def __init__(self, api_token: str):
        """
        Initialize Lichess client.

        Args:
            api_token: Personal API token from lichess.org/account/oauth/token/create
        """
        self.access_token = api_token
        self.base_url = LICHESS_API_BASE

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers with authentication."""
        headers = {"Accept": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make authenticated API request.
        
        Raises:
            requests.HTTPError: If API request fails
            ValueError: If not authenticated
        """
        if not self.access_token:
            raise ValueError("Not authenticated. Please run 'pgnc upload --auth' first.")
            
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        headers.update(kwargs.pop("headers", {}))

        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response
        except requests.HTTPError as e:
            # Try to get error message from response
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", str(e))
            except:
                error_msg = str(e)
            raise ValueError(f"Lichess API error: {error_msg}") from e
        except requests.RequestException as e:
            raise ValueError(f"Network error: {str(e)}") from e

    def get_account(self) -> Dict:
        """Get account information."""
        return self._request("GET", "/account").json()


    def import_pgn_to_study(self, study_id: str, pgn: str) -> Dict:
        """
        Import PGN content to a study using the import-pgn endpoint.

        Args:
            study_id: Lichess study ID (must exist - create manually)
            pgn: PGN content to import

        Returns:
            Response data from import

        Raises:
            ValueError: If import fails
        """
        # Lichess API endpoint: POST /api/study/{study_id}/import-pgn
        # Uses form-encoded data with 'pgn' parameter (URL-encoded)
        endpoint = f"/study/{study_id}/import-pgn"
        
        # Use form-encoded data (not JSON)
        # requests library will handle URL encoding automatically
        data = {"pgn": pgn}
        
        # Get headers but override Content-Type for form data
        headers = self._get_headers()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            
            # Try to parse JSON response, return empty dict if no content
            if response.content:
                try:
                    return response.json()
                except:
                    return {"status": "success", "content": response.text}
            return {}
        except requests.HTTPError as e:
            # Try to get error message from response
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", str(e))
            except:
                error_msg = str(e)
            raise ValueError(
                f"Failed to import PGN to study {study_id}: {error_msg}"
            ) from e
        except requests.RequestException as e:
            raise ValueError(
                f"Network error importing PGN: {str(e)}"
            ) from e


def save_token(token: str, token_file: Optional[str] = None):
    """
    Save access token to file.

    Args:
        token: Access token to save
        token_file: Path to token file (default: ~/.pgnc/lichess_token)
    """
    if token_file is None:
        token_dir = Path.home() / ".pgnc"
        token_dir.mkdir(exist_ok=True, mode=0o700)
        token_file = str(token_dir / "lichess_token")

    with open(token_file, "w") as f:
        f.write(token)

    # Set restrictive permissions
    os.chmod(token_file, 0o600)
    console.print(f"[green]✓ Token saved to {token_file}[/green]")


def load_token(token_file: Optional[str] = None) -> Optional[str]:
    """
    Load access token from file.

    Args:
        token_file: Path to token file (default: ~/.pgnc/lichess_token)

    Returns:
        Access token or None if not found
    """
    if token_file is None:
        token_file = str(Path.home() / ".pgnc" / "lichess_token")

    if not os.path.exists(token_file):
        return None

    with open(token_file, "r") as f:
        token = f.read().strip()
        # Remove any trailing newlines or whitespace
        return token.strip()


def upload_pgn_to_study(
    pgn_path: str,
    study_name: Optional[str] = None,
    api_token: Optional[str] = None,
    visibility: str = "public",
    study_id: Optional[str] = None,
) -> Dict:
    """
    Upload PGN file to Lichess study using import-pgn endpoint.

    Args:
        pgn_path: Path to PGN file
        study_name: Name for the study (default: filename, not used if study_id provided)
        api_token: Personal API token from lichess.org/account/oauth/token/create
        visibility: "public" or "private" (not used - study must exist)
        study_id: Existing study ID (REQUIRED - study must be created manually on lichess.org)

    Returns:
        Study information with ID and URL

    Note:
        Study must exist on lichess.org (create manually first).
        Each game in the PGN file will be imported as a chapter.
    """
    # Load token if not provided
    if not api_token:
        api_token = load_token()
    
    if not api_token:
        raise ValueError(
            "No API token found. Get your token from "
            "https://lichess.org/account/oauth/token/create"
        )

    if not study_id:
        raise ValueError(
            "Study ID is required. Create a study manually on lichess.org "
            "and provide the study ID from the URL."
        )

    # Initialize client
    client = LichessClient(api_token=api_token)

    # Verify authentication
    try:
        account = client.get_account()
        console.print(f"[green]✓ Authenticated as {account.get('username', 'user')}[/green]\n")
    except Exception as e:
        console.print(f"[red]✗ Authentication failed: {e}[/red]")
        raise

    # Validate PGN file
    if not os.path.exists(pgn_path):
        raise FileNotFoundError(f"PGN file not found: {pgn_path}")
    
    if not pgn_path.endswith(".pgn"):
        raise ValueError(f"File must be a PGN file: {pgn_path}")

    # Parse PGN file
    console.print(f"[cyan]Reading PGN file: {pgn_path}[/cyan]")
    try:
        games = parse_pgn(pgn_path)
    except Exception as e:
        raise ValueError(f"Failed to parse PGN file: {str(e)}") from e

    if not games:
        raise ValueError(f"No games found in {pgn_path}")

    # Use existing study (required - study must exist)
    console.print(f"\n[cyan]Importing to existing study: {study_id}[/cyan]")
    console.print("[dim]Note: Study must exist on lichess.org (create manually)[/dim]\n")

    # Upload each game as a chapter
    console.print(f"[cyan]Uploading {len(games)} game(s) as chapters...[/cyan]\n")
    chapters = []

    for i, game in enumerate(games, 1):
        # Get game name from headers
        game_name = (
            game.headers.get("White", "")
            + " vs "
            + game.headers.get("Black", "")
        )
        if not game_name or game_name == " vs ":
            game_name = f"Chapter {i}"

        console.print(f"  [{i}/{len(games)}] {game_name}")

        # Convert game to PGN string
        from chess.pgn import StringExporter
        exporter = StringExporter(headers=True, variations=True, comments=True)
        pgn_string = game.accept(exporter)

        try:
            result = client.import_pgn_to_study(study_id, pgn_string)
            chapters.append({"name": game_name, "result": result})
            console.print(f"    [green]✓[/green] Uploaded: {game_name}")
        except ValueError as e:
            console.print(f"    [red]✗[/red] Failed: {e}")
            # Continue with other chapters even if one fails
            continue
        except Exception as e:
            console.print(f"    [red]✗[/red] Unexpected error: {e}")
            continue

    study_url = f"https://lichess.org/study/{study_id}"
    console.print(f"\n[green]✓ Upload complete![/green]")
    console.print(f"Study URL: [cyan]{study_url}[/cyan]\n")

    return {
        "study_id": study_id,
        "study_name": study_name,
        "study_url": study_url,
        "chapters": len(chapters),
    }

