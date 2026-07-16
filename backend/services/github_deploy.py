"""GitHub OAuth and private repository deployment."""

from __future__ import annotations

import os
import secrets
import urllib.parse
from collections.abc import Callable
from pathlib import Path
from typing import Any

import requests

from backend.config.path_config import resolve_scan_path
from core.github_deploy import GitDeployError, deploy_fresh_source

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API = "https://api.github.com"

_oauth_states: dict[str, str] = {}
_token_sessions: dict[str, str] = {}

ProgressCallback = Callable[[str], None]


class GitHubDeployError(Exception):
    pass


class ScanWorkspaceGoneError(GitHubDeployError):
    """Raised when scan workspace no longer exists on disk."""


class GitHubDeployService:
    def __init__(self) -> None:
        self.client_id = os.getenv("GITHUB_CLIENT_ID", "")
        self.client_secret = os.getenv("GITHUB_CLIENT_SECRET", "")
        self.redirect_uri = os.getenv(
            "GITHUB_REDIRECT_URI", "http://127.0.0.1:8000/auth/callback"
        )

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def create_login_state(self) -> str:
        state = secrets.token_urlsafe(16)
        _oauth_states[state] = "pending"
        return state

    def validate_state(self, state: str) -> bool:
        return state in _oauth_states

    def authorize_url(self, state: str) -> str:
        if not self.configured:
            raise GitHubDeployError("GitHub OAuth is not configured.")
        params = urllib.parse.urlencode(
            {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "scope": "repo",
                "state": state,
            }
        )
        return f"{GITHUB_AUTH_URL}?{params}"

    def exchange_code(self, code: str, state: str) -> str:
        if not self.validate_state(state):
            raise GitHubDeployError("Invalid OAuth state.")
        if not self.configured:
            raise GitHubDeployError("GitHub OAuth is not configured.")

        resp = requests.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "redirect_uri": self.redirect_uri,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        token = data.get("access_token")
        if not token:
            raise GitHubDeployError(data.get("error_description", "OAuth token exchange failed."))

        session_id = secrets.token_urlsafe(24)
        _token_sessions[session_id] = token
        _oauth_states.pop(state, None)
        return session_id

    def get_token(self, session_id: str | None) -> str:
        if not session_id or session_id not in _token_sessions:
            raise GitHubDeployError("Unauthorized — please login with GitHub first.")
        return _token_sessions[session_id]

    @staticmethod
    def resolve_deploy_path(scan_id: str) -> Path:
        """Locate scan workspace by scan_id only."""
        path = resolve_scan_path(scan_id)
        if not path.exists() or not path.is_dir():
            raise ScanWorkspaceGoneError(
                f"Session directory [{scan_id}] no longer exists or was cleaned up."
            )
        return path

    def push_to_private_repo(
        self,
        token: str,
        repo_name: str,
        scan_id: str,
        *,
        description: str = "CodeSentinel secured deployment",
        on_progress: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        """Create a new private repo and push a fresh-source snapshot from scan_id workspace."""
        root = self.resolve_deploy_path(scan_id)

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }
        create_resp = requests.post(
            f"{GITHUB_API}/user/repos",
            headers=headers,
            json={"name": repo_name, "private": True, "description": description},
            timeout=30,
        )
        if create_resp.status_code not in (200, 201):
            raise GitHubDeployError(
                f"Failed to create repository: {create_resp.text[:500]}"
            )

        repo_data = create_resp.json()
        clone_url = repo_data.get("clone_url", "")
        html_url = repo_data.get("html_url", "")

        authed_url = clone_url.replace("https://", f"https://{token}@")

        try:
            deploy_fresh_source(root, authed_url, on_progress=on_progress)
        except GitDeployError as exc:
            raise GitHubDeployError(str(exc)) from exc

        return {"repo_url": html_url, "clone_url": clone_url, "name": repo_name, "scan_id": scan_id}
