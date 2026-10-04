"""Run the YNAB MCP server over HTTP behind GitHub sign-in, for remote connectors."""

import os

from fastmcp.server.auth import AccessToken
from fastmcp.server.auth.providers.github import GitHubProvider
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from ynab_mcp_server.server import create_server


class AllowlistGitHubProvider(GitHubProvider):
    """GitHub sign-in that only lets the listed GitHub user IDs in.

    IDs, not logins: a login can be renamed and then claimed by someone else.
    """

    def __init__(self, *, allowed_user_ids: set[str], **kwargs) -> None:
        super().__init__(**kwargs)
        self._allowed_user_ids = allowed_user_ids

    async def load_access_token(self, token: str) -> AccessToken | None:  # type: ignore[override]
        access_token = await super().load_access_token(token)
        if access_token is None:
            return None
        if access_token.claims.get("sub") not in self._allowed_user_ids:
            return None
        return access_token


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"{name} environment variable is required")
    return value


def main() -> None:
    """Run the YNAB MCP server over HTTP, requiring GitHub sign-in."""
    allowed_user_ids = {
        user_id.strip()
        for user_id in _require_env("GITHUB_ALLOWED_USER_IDS").split(",")
        if user_id.strip()
    }
    auth = AllowlistGitHubProvider(
        client_id=_require_env("GITHUB_CLIENT_ID"),
        client_secret=_require_env("GITHUB_CLIENT_SECRET"),
        base_url=_require_env("YNAB_MCP_BASE_URL"),
        # Read-only profile access; GitHubProvider's default "user" can edit it
        required_scopes=["read:user"],
        # Each request otherwise makes two GitHub API calls to check the token
        cache_ttl_seconds=300,
        allowed_user_ids=allowed_user_ids,
    )

    server = create_server(auth=auth)

    @server.custom_route("/health", methods=["GET"])
    async def health(_request: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    server.run(
        transport="http",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
    )


if __name__ == "__main__":
    main()
