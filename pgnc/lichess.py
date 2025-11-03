"""Lichess API integration for uploading studies."""

import os
import json
import secrets
import hashlib
import base64
import webbrowser
import urllib.parse
from typing import Optional, Dict, List, Tuple
from pathlib import Path

import requests
from rich.console import Console
from rich.prompt import Prompt

from .pgn_processor import parse_pgn

console = Console()

# Lichess API endpoints
LICHESS_API_BASE = "https://lichess.org/api"
LICHESS_OAUTH_BASE = "https://lichess.org/oauth"

# OAuth configuration
OAUTH_SCOPES = ["study:write"]  # Permissions needed


class LichessClient:
    """Client for interacting with Lichess API."""

    def __init__(self, access_token: Optional[str] = None, api_token: Optional[str] = None):
        """
        Initialize Lichess client.

        Args:
            access_token: OAuth access token (if using OAuth)
            api_token: Personal API token (alternative to OAuth, simpler for personal use)
        """
        # Prefer API token if provided (simpler for personal use)
        self.access_token = api_token or access_token
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

    def create_study(self, name: str, visibility: str = "public") -> Dict:
        """
        Create a new study.

        Args:
            name: Study name
            visibility: "public" or "private"

        Returns:
            Study data with ID
        """
        data = {"name": name, "visibility": visibility}
        response = self._request("POST", "/study", json=data)
        return response.json()

    def add_chapter_to_study(
        self, study_id: str, name: str, pgn: str
    ) -> Dict:
        """
        Add a chapter to a study.

        Args:
            study_id: Lichess study ID
            name: Chapter name
            pgn: PGN content

        Returns:
            Chapter data
        """
        # Lichess API endpoint for adding chapters
        data = {"name": name, "pgn": pgn}
        response = self._request(
            "POST", f"/study/{study_id}/chapters", json=data
        )
        return response.json()


def generate_pkce() -> Tuple[str, str]:
    """
    Generate PKCE code verifier and challenge for OAuth flow.

    Returns:
        Tuple of (code_verifier, code_challenge)
    """
    # Generate random code verifier
    code_verifier = base64.urlsafe_b64encode(
        secrets.token_bytes(32)
    ).decode("utf-8").rstrip("=")

    # Generate code challenge (SHA256 hash, base64url encoded)
    code_challenge = (
        base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        )
        .decode("utf-8")
        .rstrip("=")
    )

    return code_verifier, code_challenge


def get_oauth_url(code_challenge: str, state: str) -> str:
    """
    Generate OAuth authorization URL.

    Args:
        code_challenge: PKCE code challenge
        state: OAuth state parameter

    Returns:
        Authorization URL
    """
    params = {
        "response_type": "code",
        "client_id": "pgn-curator",  # This should be registered with Lichess
        "redirect_uri": "http://localhost:8080/oauth/callback",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "scope": " ".join(OAUTH_SCOPES),
        "state": state,
    }

    return f"{LICHESS_OAUTH_BASE}/authorize?" + urllib.parse.urlencode(params)


def exchange_code_for_token(
    code: str, code_verifier: str, redirect_uri: str
) -> Dict:
    """
    Exchange authorization code for access token.

    Args:
        code: Authorization code from OAuth callback
        code_verifier: PKCE code verifier
        redirect_uri: OAuth redirect URI

    Returns:
        Token response with access_token

    Raises:
        ValueError: If token exchange fails
    """
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "code_verifier": code_verifier,
        "redirect_uri": redirect_uri,
        "client_id": "pgn-curator",
    }

    try:
        response = requests.post(
            f"{LICHESS_OAUTH_BASE}/token",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        try:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", str(e))
        except:
            error_msg = str(e)
        raise ValueError(f"Token exchange failed: {error_msg}") from e
    except requests.RequestException as e:
        raise ValueError(f"Network error during token exchange: {str(e)}") from e


def authenticate() -> str:
    """
    Perform OAuth2 authentication flow.

    Returns:
        Access token
    """
    console.print("[cyan]Starting OAuth authentication with Lichess...[/cyan]\n")

    # Generate PKCE values
    code_verifier, code_challenge = generate_pkce()
    state = secrets.token_urlsafe(32)

    # Get authorization URL
    auth_url = get_oauth_url(code_challenge, state)
    console.print(f"Opening browser for authentication...")
    console.print(f"[dim]URL: {auth_url}[/dim]\n")

    # Open browser
    try:
        webbrowser.open(auth_url)
    except Exception:
        console.print(
            "[yellow]Could not open browser automatically.[/yellow]"
        )
        console.print(f"Please visit: {auth_url}\n")

    # Get authorization code from user
    console.print(
        "After authorizing, you'll be redirected to a localhost URL.\n"
        "Copy the 'code' parameter from the redirect URL.\n"
    )
    code = Prompt.ask("Enter authorization code")

    # Exchange code for token
    console.print("\n[cyan]Exchanging code for access token...[/cyan]")
    token_response = exchange_code_for_token(
        code, code_verifier, "http://localhost:8080/oauth/callback"
    )

    access_token = token_response.get("access_token")
    if access_token:
        console.print("[green]✓ Authentication successful![/green]\n")
    else:
        console.print("[red]✗ Failed to get access token[/red]")
        raise ValueError("No access token in response")

    return access_token


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
    access_token: Optional[str] = None,
    api_token: Optional[str] = None,
    visibility: str = "public",
) -> Dict:
    """
    Upload PGN file to Lichess as a study.

    Args:
        pgn_path: Path to PGN file
        study_name: Name for the study (default: filename)
        access_token: OAuth access token (deprecated, use api_token)
        api_token: Personal API token (preferred, simpler)
        visibility: "public" or "private"

    Returns:
        Study information with ID
    """
    # Load token if not provided
    token = api_token or access_token
    if not token:
        token = load_token()
    
    if not token:
        raise ValueError(
            "No API token found. Get your token from "
            "https://lichess.org/account/oauth/token/create"
        )

    # Initialize client (pass token as api_token for personal tokens)
    client = LichessClient(api_token=token)

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

    # Determine study name
    if not study_name:
        study_name = Path(pgn_path).stem.replace("_", " ").title()
    
    # Sanitize study name (Lichess may have restrictions)
    # Remove or replace invalid characters
    study_name = study_name.strip()[:100]  # Limit length
    
    if not study_name:
        study_name = "Untitled Study"

    # Create study
    console.print(f"\n[cyan]Creating study: {study_name}[/cyan]")
    try:
        study = client.create_study(study_name, visibility=visibility)
    except Exception as e:
        raise ValueError(f"Failed to create study: {str(e)}") from e
        
    # Extract study ID (Lichess may return different formats)
    study_id = (
        study.get("id") 
        or study.get("studyId") 
        or study.get("data", {}).get("id")
    )
    if not study_id:
        raise ValueError(
            f"Failed to get study ID from response. Response: {study}"
        )

    console.print(f"[green]✓ Study created: {study_id}[/green]\n")

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
            chapter = client.add_chapter_to_study(study_id, game_name, pgn_string)
            chapters.append(chapter)
            console.print(f"    [green]✓[/green] Uploaded")
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

