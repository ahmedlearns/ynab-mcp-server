"""YNAB MCP Server using FastMCP and OpenAPI specification."""

import os

import httpx
import yaml
from fastmcp import FastMCP
from fastmcp.server.providers.openapi import MCPType, OpenAPITool, RouteMap

YNAB_API_BASE = "https://api.ynab.com/v1"
YNAB_OPENAPI_SPEC_URL = "https://api.ynab.com/papi/open_api_spec.yaml"

# Route maps are checked in order; the first match wins.
ROUTE_MAPS = [
    # Returns too much data and bombs the context. YNAB renamed budgets to
    # plans in its API, so match both.
    RouteMap(
        methods=["GET"],
        pattern=r"^/(budgets/\{budget_id\}|plans/\{plan_id\})/payees$",
        mcp_type=MCPType.EXCLUDE,
    ),
    # Read-only: only GET routes become tools. Everything else, including write
    # endpoints YNAB adds to its spec later, is excluded.
    RouteMap(methods=["GET"], mcp_type=MCPType.TOOL),
    RouteMap(mcp_type=MCPType.EXCLUDE),
]


async def _reject_non_get(request: httpx.Request) -> None:
    """Second guard for read-only mode: never send a write request to YNAB."""
    if request.method != "GET":
        raise PermissionError(
            f"Read-only server refused {request.method} {request.url.path}"
        )


def _omit_openapi_output_schemas(_route: object, component: object) -> None:
    """Cursor rejects some YNAB OpenAPI response schemas; tools do not need them."""
    if isinstance(component, OpenAPITool):
        component.output_schema = None


def create_server() -> FastMCP:
    """Create and configure the YNAB MCP server from the OpenAPI spec."""
    token = os.environ.get("YNAB_API_TOKEN")
    if not token:
        raise ValueError(
            "YNAB_API_TOKEN environment variable is required. "
            "Get your personal access token from https://app.ynab.com/settings/developer"
        )

    # Fetch the OpenAPI spec from YNAB
    spec_response = httpx.get(YNAB_OPENAPI_SPEC_URL)
    spec_response.raise_for_status()
    openapi_spec = yaml.safe_load(spec_response.text)

    # Create an authenticated HTTP client
    client = httpx.AsyncClient(
        base_url=YNAB_API_BASE,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
        event_hooks={"request": [_reject_non_get]},
    )

    # Create MCP server from OpenAPI spec
    return FastMCP.from_openapi(
        openapi_spec=openapi_spec,
        client=client,
        name="YNAB MCP Server",
        route_maps=ROUTE_MAPS,
        mcp_component_fn=_omit_openapi_output_schemas,
    )


def main() -> None:
    """Run the YNAB MCP server over stdio."""
    create_server().run()


if __name__ == "__main__":
    main()
