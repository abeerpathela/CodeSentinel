"""Backward-compatible alias — use core.github_handler.GitHubHandler."""

from core.github_handler import GitHubCloneError, GitHubHandler

GitHubManager = GitHubHandler

__all__ = ["GitHubCloneError", "GitHubHandler", "GitHubManager"]
