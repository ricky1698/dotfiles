#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "rich>=13.7.0",
# ]
# ///

"""
Tailscale DevContainer Status

List all Tailscale machines tagged with 'devcontainer' and their status.
Cross-platform support for macOS, Linux, and Windows/WSL.

Usage:
    uv run ts-devcontainers.py              # Show all devcontainers
    uv run ts-devcontainers.py --online     # Show only online machines
    uv run ts-devcontainers.py --markdown   # Output as markdown table
"""

import json
import os
import platform
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()

DEVCONTAINER_TAG = "tag:devcontainer"


def is_wsl() -> bool:
    if platform.system() != "Linux":
        return False
    try:
        with open("/proc/version", "r") as f:
            return "microsoft" in f.read().lower()
    except OSError:
        return False


def get_tailscale_command() -> list[str]:
    system = platform.system()

    if system == "Windows":
        possible_paths = [
            Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
            / "Tailscale"
            / "tailscale.exe",
            Path(os.environ.get("LOCALAPPDATA", ""))
            / "Tailscale"
            / "tailscale.exe",
        ]
        for path in possible_paths:
            if path.exists():
                return [str(path)]
        return ["tailscale"]

    elif system == "Darwin":
        app_path = Path("/Applications/Tailscale.app/Contents/MacOS/Tailscale")
        if app_path.exists():
            return [str(app_path)]
        return ["tailscale"]

    elif is_wsl():
        return ["tailscale.exe"]

    else:
        return ["tailscale"]


def get_devcontainers() -> list[dict]:
    try:
        cmd = get_tailscale_command()
        result = subprocess.run(
            cmd + ["status", "--json"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            console.print(f"[red]Error: tailscale status failed[/red]")
            console.print(f"[dim]{result.stderr.strip()}[/dim]")
            sys.exit(1)

        data = json.loads(result.stdout)
        peers = data.get("Peer", {})
        self_node = data.get("Self", {})

        machines = []
        for _, node in list(peers.items()) + [("self", self_node)]:
            tags = node.get("Tags", [])
            if DEVCONTAINER_TAG not in tags:
                continue

            hostname = node.get("HostName", "")
            dns_name = node.get("DNSName", "").rstrip(".")
            online = node.get("Online", False)
            ips = node.get("TailscaleIPs", [])
            ip = ips[0] if ips else ""
            os_info = node.get("OS", "")

            machines.append({
                "hostname": hostname,
                "dns_name": dns_name,
                "ip": ip,
                "os": os_info,
                "online": online,
            })

        machines.sort(key=lambda m: (not m["online"], m["hostname"]))
        return machines

    except FileNotFoundError:
        console.print("[red]Error: tailscale command not found[/red]")
        system = platform.system()
        if is_wsl():
            console.print("[yellow]  WSL: Install Tailscale on Windows host[/yellow]")
        elif system == "Darwin":
            console.print("[yellow]  macOS: brew install tailscale[/yellow]")
        else:
            console.print("[yellow]  https://tailscale.com/download[/yellow]")
        sys.exit(1)
    except json.JSONDecodeError as e:
        console.print(f"[red]Error: Failed to parse Tailscale output: {e}[/red]")
        sys.exit(1)


def print_rich_table(machines: list[dict]) -> None:
    table = Table(title="DevContainers on Tailnet")
    table.add_column("Machine", style="cyan")
    table.add_column("DNS Name", style="white")
    table.add_column("Tailscale IP", style="white")
    table.add_column("OS", style="dim")
    table.add_column("Status", justify="center")

    for m in machines:
        status = "[green]● Active[/green]" if m["online"] else "[red]● Stopped[/red]"
        table.add_row(m["hostname"], m["dns_name"], m["ip"], m["os"], status)

    console.print(table)
    console.print(f"\n[dim]Total: {len(machines)} machines, "
                  f"{sum(1 for m in machines if m['online'])} online[/dim]")


def print_markdown_table(machines: list[dict]) -> None:
    print("| Machine | DNS Name | Tailscale IP | OS | Status |")
    print("|---------|----------|-------------|-----|--------|")
    for m in machines:
        emoji = "🟢" if m["online"] else "🔴"
        status = "Active" if m["online"] else "Stopped"
        print(f"| {m['hostname']} | {m['dns_name']} | {m['ip']} | {m['os']} | {emoji} {status} |")


def main() -> None:
    markdown = "--markdown" in sys.argv or "-m" in sys.argv
    online_only = "--online" in sys.argv or "-o" in sys.argv

    machines = get_devcontainers()

    if online_only:
        machines = [m for m in machines if m["online"]]

    if not machines:
        console.print("[yellow]No devcontainer machines found[/yellow]")
        sys.exit(0)

    if markdown:
        print_markdown_table(machines)
    else:
        print_rich_table(machines)


if __name__ == "__main__":
    main()
