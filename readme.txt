# EVE-NG Lab Automation MCP Server

Automate EVE-NG lab topology creation via the REST API, directly from Claude Desktop.

---

## What It Does

This MCP server exposes EVE-NG's REST API as natural-language tools that Claude can call.
You can say things like:

- "Log in to my EVE-NG server at 192.168.1.50 with admin/eve"
- "Create a new CCNP pentest lab called WebHack-Lab"
- "Build a full CCNP web pentest topology with vIOS routers and switches"
- "Add a Kali Linux node to the PentestVLAN"
- "Start all nodes in /WebHack-Lab.unl"
- "List all templates available on my EVE-NG instance"

---

## Architecture

```
Claude Desktop
    └── MCP Gateway (Docker)
            └── eveng-mcp-server (Docker container)
                    └── EVE-NG REST API  (http(s)://your-eve-ng-host/api/...)
```

Authentication uses EVE-NG's cookie-based session system:
- POST /api/auth/login -> receives a session cookie
- All subsequent requests carry that cookie
- Cookies are stored in memory for the lifetime of the container

---

## Available Tools

| Tool | Description |
|------|-------------|
| `eve_login` | Log in to EVE-NG and establish a session |
| `eve_logout` | Log out and clear session |
| `eve_status` | Get CPU/RAM/disk/node status |
| `eve_list_templates` | List all node templates (vios, viosl2, linux, etc.) |
| `eve_list_networks` | List available network types |
| `eve_list_labs` | Browse folders and labs |
| `eve_create_lab` | Create a new lab |
| `eve_get_lab` | Get lab details |
| `eve_delete_lab` | Delete a lab |
| `eve_list_nodes` | List nodes in a lab |
| `eve_add_node` | Add a node (router, switch, server) |
| `eve_delete_node` | Remove a node |
| `eve_start_nodes` | Start all or a single node |
| `eve_stop_nodes` | Stop all or a single node |
| `eve_list_lab_networks` | List networks in a lab |
| `eve_add_network` | Add a network segment to a lab |
| `eve_list_links` | Show all connectable endpoints |
| `eve_connect_node_to_network` | Connect a node interface to a network |
| `eve_get_node_interfaces` | Show node interface assignments |
| `eve_build_ccnp_pentest_topology` | **One-shot**: build a full CCNP pentest topology |
| `eve_add_pentest_nodes` | Add Kali + target server to an existing topology |

---

## CCNP Pentest Topology

Running `eve_build_ccnp_pentest_topology` creates:

```
  MGMT-Cloud (pnet0 - connects to your real network)
       |
  CORE-R1 (vIOS Router) ---- EDGE-R2 (vIOS Router)
       |                    (WAN-Link segment)
       |── DMZ (bridge) - for internet-facing servers
       |
  DIST-SW1 (vIOS-L2 Distribution Switch)
       |
  ACCESS-SW1 (vIOS-L2 Access Switch)
       |── ServerVLAN (bridge) - deploy DVWA, Metasploitable, etc.
       └── PentestVLAN (bridge) - deploy Kali Linux here
```

After the topology is built, add Linux nodes to the VLAN segments to simulate
a real corporate network environment for web penetration testing practice.

---

## Prerequisites

1. A running EVE-NG Community or Pro instance
2. vIOS and vIOS-L2 images installed on EVE-NG (requires Cisco licensing)
3. Linux images uploaded to EVE-NG (Kali, Metasploitable, DVWA, etc.)
4. Docker installed on your machine
5. Claude Desktop with Docker MCP gateway configured

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EVE_HOST` | `http://192.168.1.1` | EVE-NG base URL |
| `EVE_USER` | `admin` | EVE-NG username |
| `EVE_PASS` | `eve` | EVE-NG password |
| `EVE_PRO` | `false` | Set to `true` for Pro edition (adds html5=0 to login, skips SSL verify) |

---

## Quick Start

```bash
# 1. Build the image
docker build -t eveng-mcp-server .

# 2. Set secrets
docker mcp secret set EVE_HOST="http://192.168.1.50"
docker mcp secret set EVE_USER="admin"
docker mcp secret set EVE_PASS="yourpassword"

# 3. Add to custom catalog and restart Claude Desktop (see INSTALLATION section)
```

---

## Educational Pentest Lab Workflow

```
1. eve_login           -> authenticate
2. eve_list_templates  -> confirm vios, viosl2, linux images exist
3. eve_build_ccnp_pentest_topology(lab_name="WebPentest-Lab")
4. eve_list_lab_networks(lab_path="/WebPentest-Lab.unl")  -> get PentestVLAN and ServerVLAN IDs
5. eve_add_pentest_nodes(lab_path=..., kali_net_id=..., target_net_id=...)
6. eve_start_nodes(lab_path="/WebPentest-Lab.unl")
7. Open EVE-NG web UI -> console into nodes -> configure IPs and start testing
```

---

## Security Notes

- This server is intended for use against your **own** isolated lab environment only.
- Never point the PentestVLAN at production networks.
- The MGMT-Cloud (pnet0) connection is optional and can be removed if you want a fully isolated lab.
- SSL verification is disabled by default to accommodate self-signed EVE-NG Pro certificates.

---

## License

MIT - For educational use.
