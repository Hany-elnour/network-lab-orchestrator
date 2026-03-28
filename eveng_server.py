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
# TEMPLATES & NETWORK TYPES
# ============================================================

@mcp.tool()
async def eve_list_templates(template: str = "") -> str:
    """List all available node templates, or full details for a specific template name."""
    path = f"/list/templates/{template.strip()}" if template.strip() else "/list/templates/"
    if template.strip():
        logger.info(f"[TEMPLATES] Fetching details for template '{template.strip()}'")
    else:
        logger.info("[TEMPLATES] Fetching all available templates")
    try:
        async with _client() as c:
            r = await c.get(f"{_base_url()}{path}")
            data = r.json()
        if _ok(data):
            count = len(data["data"]) if isinstance(data["data"], dict) else "?"
            logger.info(f"[TEMPLATES] Returned {count} template(s)")
            return f"📋 Templates:\n{_fmt(data['data'])}"
        logger.warning(f"[TEMPLATES] API error: {data.get('message', 'Unknown error')}")
        return f"❌ {data.get('message', 'Unknown error')}"
    except Exception as e:
        logger.error(f"[TEMPLATES] Exception: {e}")
        return f"❌ Error: {e}"


@mcp.tool()
async def eve_list_networks() -> str:
    """List all available network types (bridge, ovs, pnet0-9)."""
    logger.info("[NETWORKS] Fetching available network types")
    try:
        async with _client() as c:
            r = await c.get(f"{_base_url()}/list/networks")
            data = r.json()
        if _ok(data):
            logger.info(f"[NETWORKS] Returned {len(data['data'])} network type(s)")
            return f"🌐 Network types:\n{_fmt(data['data'])}"
        logger.warning(f"[NETWORKS] API error: {data.get('message', 'Unknown error')}")
        return f"❌ {data.get('message', 'Unknown error')}"
    except Exception as e:
        logger.error(f"[NETWORKS] Exception: {e}")
        return f"❌ Error: {e}"


# ============================================================
# LAB MANAGEMENT
# ============================================================

@mcp.tool()
async def eve_list_labs(folder: str = "") -> str:
    """List labs and subfolders inside a folder path (default: root /)."""
    folder_path = folder.strip("/").strip()
    logger.info(f"[LABS] Listing labs in folder: '/{folder_path or ''}'")
    try:
        async with _client() as c:
            r = await c.get(f"{_base_url()}/folders/{folder_path}")
            data = r.json()
        if _ok(data):
            d = data["data"]
            folders = d.get("folders", [])
            labs    = d.get("labs", [])
            logger.info(f"[LABS] Found {len(folders)} subfolder(s) and {len(labs)} lab(s)")
            lines = ["📁 Folders:"]
            for f in folders:
                lines.append(f"  {f['name']} -> {f['path']}")
            lines.append("🧪 Labs:")
            for lab in labs:
                lines.append(f"  {lab['file']} -> {lab['path']}")
            return "\n".join(lines)
        logger.warning(f"[LABS] API error: {data.get('message', 'Unknown error')}")
        return f"❌ {data.get('message', 'Unknown error')}"
    except Exception as e:
        logger.error(f"[LABS] Exception: {e}")
        return f"❌ Error: {e}"


@mcp.tool()
async def eve_create_lab(
    name: str = "",
    path: str = "/",
    description: str = "",
    author: str = "",
    version: str = "1",
) -> str:
    """Create a new EVE-NG lab at the specified folder path."""
    if not name.strip():
        return "❌ Lab name is required"
    payload = {
        "path": path.strip() or "/",
        "name": name.strip(),
        "version": version.strip() or "1",
        "description": description.strip(),
        "author": author.strip(),
        "body": "",
    }
    logger.info(f"[LAB] Creating lab '{name}' at path '{path}'")
    try:
        async with _client() as c:
            r = await c.post(f"{_base_url()}/labs", json=payload)
            data = r.json()
        if _ok(data):
            logger.info(f"[LAB] Lab '{name}' created successfully")
            return f"✅ Lab '{name}' created at {path}"
        logger.warning(f"[LAB] Failed to create lab '{name}': {data.get('message', 'Unknown error')}")
        return f"❌ {data.get('message', 'Unknown error')}"
    except Exception as e:
        logger.error(f"[LAB] Exception creating lab '{name}': {e}")
        return f"❌ Error: {e}"


@mcp.tool()
async def eve_get_lab(lab_path: str = "") -> str:
    """Get details of an existing lab by its full path (e.g. /folder/lab.unl)."""
    if not lab_path.strip():
        return "❌ lab_path is required (e.g. /folder/lab.unl)"
    logger.info(f"[LAB] Fetching details for lab: {lab_path}")
    try:
        async with _client() as c:
            r = await c.get(f"{_base_url()}/labs/{_encode_path(lab_path)}")
            data = r.json()
        if _ok(data):
            logger.info(f"[LAB] Successfully retrieved lab info for: {lab_path}")
            return f"🧪 Lab info:\n{_fmt(data['data'])}"
        logger.warning(f"[LAB] Could not fetch lab '{lab_path}': {data.get('message', 'Unknown error')}")
        return f"❌ {data.get('message', 'Unknown error')}"
    except Exception as e:
        logger.error(f"[LAB] Exception fetching lab '{lab_path}': {e}")
        return f"❌ Error: {e}"


@mcp.tool()
async def eve_delete_lab(lab_path: str = "") -> str:
    """Delete a lab by its full path (e.g. /folder/lab.unl)."""
    if not lab_path.strip():
        return "❌ lab_path is required"
    logger.info(f"[LAB] Deleting lab: {lab_path}")
    try:
        async with _client() as c:
            r = await c.delete(f"{_base_url()}/labs/{_encode_path(lab_path)}")
            data = r.json()
        if _ok(data):
            logger.info(f"[LAB] Lab deleted: {lab_path}")
            return f"✅ Lab deleted: {lab_path}"
        logger.warning(f"[LAB] Failed to delete lab '{lab_path}': {data.get('message', 'Unknown error')}")
        return f"❌ {data.get('message', 'Unknown error')}"
    except Exception as e:
        logger.error(f"[LAB] Exception deleting lab '{lab_path}': {e}")
        return f"❌ Error: {e}"


# ============================================================
# NODE MANAGEMENT
# ============================================================

@mcp.tool()
async def eve_list_nodes(lab_path: str = "") -> str:
    """List all nodes in a lab."""
    if not lab_path.strip():
        return "❌ lab_path is required"
    logger.info(f"[NODES] Listing nodes in lab: {lab_path}")
    try:
        async with _client() as c:
            r = await c.get(f"{_base_url()}/labs/{_encode_path(lab_path)}/nodes")
            data = r.json()
        if _ok(data):
            nodes = data["data"]
            logger.info(f"[NODES] Found {len(nodes)} node(s) in {lab_path}")
            lines = [f"🖥️  Nodes in {lab_path}:"]
            for nid, n in nodes.items():
                lines.append(
                    f"  [{nid}] {n.get('name','?')}"
                    f" | template={n.get('template','?')}"
                    f" | status={n.get('status','?')}"
                    f" | url={n.get('url','N/A')}"
                )
            return "\n".join(lines)
        logger.warning(f"[NODES] API error: {data.get('message', 'Unknown error')}")
        return f"❌ {data.get('message', 'Unknown error')}"
    except Exception as e:
        logger.error(f"[NODES] Exception listing nodes in '{lab_path}': {e}")
        return f"❌ Error: {e}"


@mcp.tool()
async def eve_add_node(
    lab_path: str = "",
    template: str = "",
    name: str = "",
    image: str = "",
    ram: str = "512",
    cpu: str = "1",
    ethernet: str = "4",
    left: str = "200",
    top: str = "200",
    icon: str = "Router.png",
) -> str:
    """
    Add a node to a lab. Returns the new node ID.

    Common templates: vios (IOS router), viosl2 (IOS L2 switch),
    linux (Linux VM), win (Windows VM).
    Leave `image` empty to use the template default.
    """
    if not lab_path.strip():
        return "❌ lab_path is required"
    if not template.strip():
        return "❌ template is required (e.g. vios, viosl2, linux)"

    node_name = name.strip() or template.strip().upper()
    payload = {
        "template": template.strip(),
        "type":     "qemu",
        "name":     node_name,
        "image":    image.strip(),
        "ram":      int(ram)      if ram.strip().isdigit()      else 512,
        "cpu":      int(cpu)      if cpu.strip().isdigit()      else 1,
        "ethernet": int(ethernet) if ethernet.strip().isdigit() else 4,
        "left":     int(left)     if left.strip().isdigit()     else 200,
        "top":      int(top)      if top.strip().isdigit()      else 200,
        "icon":     icon.strip()  or "Router.png",
        "config":   "Unconfigured",
        "delay":    0,
    }
    logger.info(
        f"[NODE] Adding node '{node_name}' (template={template}) "
        f"to lab '{lab_path}' — RAM={payload['ram']}MB CPU={payload['cpu']} ETH={payload['ethernet']}"
    )
    try:
        async with _client() as c:
            r = await c.post(
                f"{_base_url()}/labs/{_encode_path(lab_path)}/nodes",
                json=payload,
            )
            data = r.json()
        if _ok(data):
            node_id = data.get("data", {}).get("id", "?")
            logger.info(f"[NODE] Node '{node_name}' created with ID {node_id}")
            return f"✅ Node '{node_name}' added. Node ID: {node_id}"
        logger.warning(f"[NODE] Failed to add node '{node_name}': {data.get('message', 'Unknown error')}")
        return f"❌ {data.get('message', 'Unknown error')}"
    except Exception as e:
        logger.error(f"[NODE] Exception adding node '{node_name}': {e}")
        return f"❌ Error: {e}"


@mcp.tool()
async def eve_delete_node(lab_path: str = "", node_id: str = "") -> str:
    """Delete a node from a lab by its node ID."""
    if not lab_path.strip() or not node_id.strip():
        return "❌ lab_path and node_id are required"
    logger.info(f"[NODE] Deleting node ID {node_id} from lab '{lab_path}'")
    try:
        async with _client() as c:
            r = await c.delete(
                f"{_base_url()}/labs/{_encode_path(lab_path)}/nodes/{node_id.strip()}"
            )
            data = r.json()
        if _ok(data):
            logger.info(f"[NODE] Node {node_id} deleted from '{lab_path}'")
            return f"✅ Node {node_id} deleted from {lab_path}"
        logger.warning(f"[NODE] Failed to delete node {node_id}: {data.get('message', 'Unknown error')}")
        return f"❌ {data.get('message', 'Unknown error')}"
    except Exception as e:
        logger.error(f"[NODE] Exception deleting node {node_id}: {e}")
        return f"❌ Error: {e}"


@mcp.tool()
async def eve_start_nodes(lab_path: str = "", node_id: str = "") -> str:
    """Start all nodes in a lab, or a single node when node_id is provided."""
    if not lab_path.strip():
        return "❌ lab_path is required"
    base = f"{_base_url()}/labs/{_encode_path(lab_path)}/nodes"
    url  = f"{base}/{node_id.strip()}/start" if node_id.strip() else f"{base}/start"
    target = f"node {node_id}" if node_id.strip() else "all nodes"
    logger.info(f"[NODE] Starting {target} in lab '{lab_path}'")
    try:
        async with _client() as c:
            r = await c.get(url)
            data = r.json()
        if _ok(data):
            logger.info(f"[NODE] Successfully started {target} in '{lab_path}'")
            return f"⚡ Started {target} in {lab_path}"
        logger.warning(f"[NODE] Failed to start {target}: {data.get('message', 'Unknown error')}")
        return f"❌ {data.get('message', 'Unknown error')}"
    except Exception as e:
        logger.error(f"[NODE] Exception starting {target}: {e}")
        return f"❌ Error: {e}"


@mcp.tool()
async def eve_stop_nodes(lab_path: str = "", node_id: str = "") -> str:
    """Stop all nodes in a lab, or a single node when node_id is provided."""
    if not lab_path.strip():
        return "❌ lab_path is required"
    base = f"{_base_url()}/labs/{_encode_path(lab_path)}/nodes"
    url  = f"{base}/{node_id.strip()}/stop" if node_id.strip() else f"{base}/stop"
    target = f"node {node_id}" if node_id.strip() else "all nodes"
    logger.info(f"[NODE] Stopping {target} in lab '{lab_path}'")
    try:
        async with _client() as c:
            r = await c.get(url)
            data = r.json()
        if _ok(data):
            logger.info(f"[NODE] Successfully stopped {target} in '{lab_path}'")
            return f"🛑 Stopped {target} in {lab_path}"
        logger.warning(f"[NODE] Failed to stop {target}: {data.get('message', 'Unknown error')}")
        return f"❌ {data.get('message', 'Unknown error')}"
    except Exception as e:
        logger.error(f"[NODE] Exception stopping {target}: {e}")
        return f"❌ Error: {e}"


# ============================================================
# NETWORK MANAGEMENT
# ============================================================

@mcp.tool()
async def eve_list_lab_networks(lab_path: str = "") -> str:
    """List all networks (bridges/OVS/cloud) configured in a lab."""
    if not lab_path.strip():
        return "❌ lab_path is required"
    logger.info(f"[NETWORK] Listing networks in lab: {lab_path}")
    try:
        async with _client() as c:
            r = await c.get(f"{_base_url()}/labs/{_encode_path(lab_path)}/networks")
            data = r.json()
        if _ok(data):
            logger.info(f"[NETWORK] Found {len(data['data'])} network(s) in '{lab_path}'")
            return f"🌐 Networks in {lab_path}:\n{_fmt(data['data'])}"
        logger.warning(f"[NETWORK] API error: {data.get('message', 'Unknown error')}")
        return f"❌ {data.get('message', 'Unknown error')}"
    except Exception as e:
        logger.error(f"[NETWORK] Exception listing networks in '{lab_path}': {e}")
        return f"❌ Error: {e}"


@mcp.tool()
async def eve_add_network(
    lab_path: str = "",
    name: str = "",
    net_type: str = "bridge",
    left: str = "400",
    top: str = "300",
) -> str:
    """
    Add a network segment to a lab. Returns the new network ID.

    net_type options: bridge, ovs, pnet0 … pnet9.
    Use pnet0 to connect to the EVE-NG management interface (cloud).
    """
    if not lab_path.strip() or not name.strip():
        return "❌ lab_path and name are required"
    payload = {
        "name": name.strip(),
        "type": net_type.strip() or "bridge",
        "left": int(left) if left.strip().isdigit() else 400,
        "top":  int(top)  if top.strip().isdigit()  else 300,
    }
    logger.info(f"[NETWORK] Adding network '{name}' (type={net_type}) to lab '{lab_path}'")
    try:
        async with _client() as c:
            r = await c.post(
                f"{_base_url()}/labs/{_encode_path(lab_path)}/networks",
                json=payload,
            )
            data = r.json()
        if _ok(data):
            net_id = data.get("data", {}).get("id", "?")
            logger.info(f"[NETWORK] Network '{name}' created with ID {net_id}")
            return f"✅ Network '{name}' (type={net_type}) added. Network ID: {net_id}"
        logger.warning(f"[NETWORK] Failed to add network '{name}': {data.get('message', 'Unknown error')}")
        return f"❌ {data.get('message', 'Unknown error')}"
    except Exception as e:
        logger.error(f"[NETWORK] Exception adding network '{name}': {e}")
        return f"❌ Error: {e}"


# ============================================================
# CONNECTIONS
# ============================================================

@mcp.tool()
async def eve_list_links(lab_path: str = "") -> str:
    """List all available ethernet/serial endpoints in a lab (useful before wiring nodes)."""
    if not lab_path.strip():
        return "❌ lab_path is required"
    logger.info(f"[LINKS] Listing available endpoints in lab: {lab_path}")
    try:
        async with _client() as c:
            r = await c.get(f"{_base_url()}/labs/{_encode_path(lab_path)}/links")
            data = r.json()
        if _ok(data):
            logger.info(f"[LINKS] Retrieved endpoint list for '{lab_path}'")
            return f"🔗 Available endpoints in {lab_path}:\n{_fmt(data['data'])}"
        logger.warning(f"[LINKS] API error: {data.get('message', 'Unknown error')}")
        return f"❌ {data.get('message', 'Unknown error')}"
    except Exception as e:
        logger.error(f"[LINKS] Exception listing links in '{lab_path}': {e}")
        return f"❌ Error: {e}"


@mcp.tool()
async def eve_get_node_interfaces(lab_path: str = "", node_id: str = "") -> str:
    """Get all interfaces of a node and their current network assignments."""
    if not lab_path.strip() or not node_id.strip():
        return "❌ lab_path and node_id are required"
    logger.info(f"[IFACE] Fetching interfaces for node {node_id} in lab '{lab_path}'")
    try:
        async with _client() as c:
            r = await c.get(
                f"{_base_url()}/labs/{_encode_path(lab_path)}/nodes/{node_id.strip()}/interfaces"
            )
            data = r.json()
        if _ok(data):
            logger.info(f"[IFACE] Retrieved interface assignments for node {node_id}")
            return f"🔌 Interfaces for node {node_id}:\n{_fmt(data['data'])}"
        logger.warning(f"[IFACE] API error for node {node_id}: {data.get('message', 'Unknown error')}")
        return f"❌ {data.get('message', 'Unknown error')}"
    except Exception as e:
        logger.error(f"[IFACE] Exception fetching interfaces for node {node_id}: {e}")
        return f"❌ Error: {e}"


@mcp.tool()
async def eve_connect_node_to_network(
    lab_path: str = "",
    node_id: str = "",
    interface_id: str = "0",
    network_id: str = "",
) -> str:
    """
    Connect a node interface to a network segment.

    interface_id: zero-based ethernet port index (e.g. 0 = Gi0/0, 1 = Gi0/1).
    network_id: ID returned by eve_add_network or eve_list_lab_networks.
    """
    if not lab_path.strip() or not node_id.strip() or not network_id.strip():
        return "❌ lab_path, node_id, and network_id are all required"
    logger.info(
        f"[CONNECT] Wiring node {node_id} interface {interface_id} "
        f"-> network {network_id} in lab '{lab_path}'"
    )
    payload = {interface_id.strip(): int(network_id.strip())}
    try:
        async with _client() as c:
            r = await c.put(
                f"{_base_url()}/labs/{_encode_path(lab_path)}/nodes/{node_id.strip()}/interfaces",
                json=payload,
            )
            data = r.json()
        if _ok(data):
            logger.info(f"[CONNECT] Node {node_id} iface {interface_id} connected to network {network_id}")
            return f"✅ Node {node_id} interface {interface_id} -> network {network_id}"
        logger.warning(
            f"[CONNECT] Failed to wire node {node_id} iface {interface_id} "
            f"-> network {network_id}: {data.get('message', 'Unknown error')}"
        )
        return f"❌ {data.get('message', 'Unknown error')}"
    except Exception as e:
        logger.error(f"[CONNECT] Exception wiring node {node_id}: {e}")
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
