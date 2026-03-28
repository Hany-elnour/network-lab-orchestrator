#!/usr/bin/env python3
"""
EVE-NG Lab Automation MCP Server
Automates EVE-NG lab topology creation via the REST API.
"""

import os
import sys
import json
import logging
import httpx
from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("eveng-server")

mcp = FastMCP("eveng")

EVE_HOST = os.environ.get("EVE_HOST", "")
EVE_USER = os.environ.get("EVE_USER", "")
EVE_PASS = os.environ.get("EVE_PASS", "")
EVE_PRO  = os.environ.get("EVE_PRO", "false").lower() == "true"

_session_cookies: dict = {}


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _base_url() -> str:
    return f"{EVE_HOST.rstrip('/')}/api"


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        cookies=_session_cookies.get(EVE_HOST, {}),
        verify=False,
        timeout=30,
    )


def _save_cookies(response: httpx.Response) -> None:
    _session_cookies[EVE_HOST] = dict(response.cookies)


def _fmt(data: object) -> str:
    return json.dumps(data, indent=2)


def _encode_path(lab_path: str) -> str:
    """Strip leading slash and percent-encode spaces for use in URLs."""
    return lab_path.strip().lstrip("/").replace(" ", "%20")


def _ok(data: dict) -> bool:
    return data.get("status") == "success"


# ============================================================
# AUTH
# ============================================================

@mcp.tool()
async def eve_login(host: str = "", username: str = "", password: str = "") -> str:
    """Login to EVE-NG and store the session cookie for subsequent API calls."""
    global EVE_HOST, EVE_USER, EVE_PASS
    if host.strip():
        EVE_HOST = host.strip().rstrip("/")
    if username.strip():
        EVE_USER = username.strip()
    if password.strip():
        EVE_PASS = password.strip()

    payload: dict = {"username": EVE_USER, "password": EVE_PASS}
    if EVE_PRO:
        payload["html5"] = "0"

    logger.info(f"[AUTH] Attempting login to {EVE_HOST} as '{EVE_USER}'")
    try:
        async with _client() as c:
            r = await c.post(f"{_base_url()}/auth/login", json=payload)
            _save_cookies(r)
            data = r.json()
            if _ok(data):
                logger.info(f"[AUTH] Login successful — session cookie saved for {EVE_HOST}")
                return f"✅ Logged in to {EVE_HOST} as {EVE_USER}"
            logger.warning(f"[AUTH] Login failed: {data.get('message', 'Unknown error')}")
            return f"❌ Login failed: {data.get('message', 'Unknown error')}"
    except Exception as e:
        logger.error(f"[AUTH] Login exception: {e}")
        return f"❌ Login error: {e}"


@mcp.tool()
async def eve_logout() -> str:
    """Logout from EVE-NG and clear the local session cookie."""
    logger.info(f"[AUTH] Logging out from {EVE_HOST}")
    try:
        async with _client() as c:
            await c.get(f"{_base_url()}/auth/logout")
        _session_cookies.pop(EVE_HOST, None)
        logger.info("[AUTH] Session cookie cleared")
        return f"✅ Logged out from {EVE_HOST}"
    except Exception as e:
        logger.error(f"[AUTH] Logout exception: {e}")
        return f"❌ Logout error: {e}"


@mcp.tool()
async def eve_status() -> str:
    """Get EVE-NG system status including CPU, RAM, disk, and running nodes."""
    logger.info(f"[STATUS] Fetching system status from {EVE_HOST}")
    try:
        async with _client() as c:
            r = await c.get(f"{_base_url()}/status")
            data = r.json()
        if _ok(data):
            s = data["data"]
            logger.info(
                f"[STATUS] CPU={s.get('cpu')}% MEM={s.get('mem')}% "
                f"DISK={s.get('disk')}% QEMU={s.get('qemu',0)} "
                f"IOL={s.get('iol',0)} Dynamips={s.get('dynamips',0)}"
            )
            return (
                f"📊 EVE-NG Status\n"
                f"  Version  : {s.get('version', 'N/A')}\n"
                f"  CPU      : {s.get('cpu', 'N/A')}%\n"
                f"  Memory   : {s.get('mem', 'N/A')}%\n"
                f"  Disk     : {s.get('disk', 'N/A')}%\n"
                f"  QEMU VMs : {s.get('qemu', 0)} running\n"
                f"  IOL      : {s.get('iol', 0)} running\n"
                f"  Dynamips : {s.get('dynamips', 0)} running"
            )
        logger.warning(f"[STATUS] API error: {data.get('message', 'Unknown error')}")
        return f"❌ {data.get('message', 'Unknown error')}"
    except Exception as e:
        logger.error(f"[STATUS] Exception: {e}")
        return f"❌ Error: {e}"



# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    logger.info("Starting EVE-NG MCP server...")
    logger.info(f"Target host : {EVE_HOST}")
    logger.info(f"User        : {EVE_USER}")
    if not EVE_PASS:
        logger.warning("EVE_PASS not set — use eve_login tool to authenticate at runtime")
    try:
        mcp.run(transport="stdio")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
