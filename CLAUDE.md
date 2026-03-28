# CLAUDE.md — EVE-NG MCP Server Implementation Notes

## Overview

This MCP server wraps the EVE-NG REST API. All tools return plain strings.
Authentication is cookie-based (not token-based). The session cookie must be
acquired via `eve_login` before any other tool will work.

---

## Authentication Model

EVE-NG uses cookie sessions, NOT Bearer tokens.

Login flow:
```
POST /api/auth/login
Body: {"username": "admin", "password": "eve"}
Response sets a session cookie (e.g. unetlab_session=abc123)
All subsequent requests must send that cookie
```

For EVE-NG Pro:
```
POST /api/auth/login
Body: {"username": "admin", "password": "eve", "html5": "0"}
Use HTTPS, ignore SSL cert errors (self-signed is common)
```

The server stores cookies in a module-level dict `_session_cookies` keyed by
EVE_HOST. The `_get_client()` helper injects these into every httpx request.

---

## Node Templates

Key template names used in this server:
- `vios`   — Cisco vIOS Router (QEMU)
- `viosl2` — Cisco vIOS L2 Switch (QEMU)
- `linux`  — Generic Linux (QEMU) — used for Kali, Metasploitable, DVWA, etc.

Image names are installation-specific. Use `eve_list_templates("vios")` to
discover what images are installed on the target EVE-NG instance.

---

## Lab Path Encoding

EVE-NG API paths are URL-encoded. The convention used in this server:
```python
encoded = lab_path.strip().lstrip("/").replace(" ", "%20")
url = f"{_base_url()}/labs/{encoded}/nodes"
```

The raw path (e.g. `/MyFolder/My Lab.unl`) is stored unencoded in `base_lab`
and shown to the user. The encoded form is only used for API URLs.

---

## Node Interface Numbering

EVE-NG ethernet interfaces are 0-indexed:
- Interface 0 = Gi0/0 (first Ethernet)
- Interface 1 = Gi0/1
- etc.

The connect API call format:
```
PUT /api/labs/{lab_path}/nodes/{node_id}/interfaces
Body: {"0": 3}  <- interface 0 connected to network ID 3
```

---

## CCNP Pentest Topology Details

`eve_build_ccnp_pentest_topology` creates this network in one shot:

Nodes:
- CORE-R1  (vios, 4 eth)
- EDGE-R2  (vios, 4 eth)
- DIST-SW1 (viosl2, 8 eth)
- ACCESS-SW1 (viosl2, 8 eth)

Networks:
- MGMT-Cloud  (pnet0) — out-of-band mgmt, bridges to physical NIC
- WAN-Link    (bridge) — CORE-R1 <-> EDGE-R2
- Core-Dist   (bridge) — CORE-R1 <-> DIST-SW1
- Dist-Access (bridge) — DIST-SW1 <-> ACCESS-SW1
- ServerVLAN  (bridge) — attach target Linux servers here
- PentestVLAN (bridge) — attach Kali / attacker here
- DMZ         (bridge) — attach DMZ-facing servers here

All connections are wired inside the same function using the PUT interfaces
endpoint after all nodes and networks are created.

---

## EVE-NG API Response Pattern

All responses follow JSend:
```json
{"code": 200, "status": "success", "data": {...}, "message": "..."}
{"code": 404, "status": "fail", "message": "..."}
```

Check `data.get("status") == "success"` for success, not the HTTP status code.
The HTTP status code and the `code` field in JSON are usually the same but rely
on the JSON `status` field for logic.

---

## Adding New Tools

Follow this pattern exactly:

```python
@mcp.tool()
async def eve_my_tool(param: str = "") -> str:
    """Single-line description — NO multi-line docstrings."""
    if not param.strip():
        return "❌ Error: param is required"
    encoded = param.strip().lstrip("/").replace(" ", "%20")
    url = f"{_base_url()}/some/endpoint/{encoded}"
    try:
        async with _get_client() as client:
            resp = await client.get(url)
            data = resp.json()
            if data.get("status") == "success":
                return f"✅ Result:\n{_fmt(data['data'])}"
            return f"❌ {data.get('message', 'Unknown error')}"
    except Exception as e:
        return f"❌ Error: {str(e)}"
```

Rules:
- SINGLE-LINE docstrings only (multi-line causes gateway panic)
- Use `str` defaults only, no `None`, no `Optional`
- Always return a string
- Always use `async with _get_client() as client:`
- Log actions with `logger.info()`

---

## Environment Variable Reference

| Variable | Purpose |
|----------|---------|
| EVE_HOST | Full URL including protocol, e.g. http://192.168.1.50 |
| EVE_USER | Login username |
| EVE_PASS | Login password |
| EVE_PRO  | "true" enables Pro login payload and disables SSL verify |

These can be overridden at runtime via `eve_login(host=..., username=..., password=...)`.

---

## Known Limitations

1. Session cookies are in-memory only — container restart requires re-login.
2. Image names are environment-specific; the `image` field is left blank in
   add_node calls so EVE-NG uses the template default. Pass the exact image
   string via `eve_add_node(image="vios-adventerprisek9-m-15.6...")` if needed.
3. The EVE-NG API docs are partially outdated; use browser devtools on the
   EVE-NG web UI to spy on exact request/response shapes for newer features.
4. `pnet0` MGMT-Cloud requires that pnet0 is bridged to a physical interface
   in EVE-NG's network configuration.
