#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.21.1",
#     "rich>=13.7.0",
# ]
# ///

"""
Tailscale Machine Selector

Select a Tailscale machine using fzf and copy DNS name to clipboard.

Usage:
    ts.py                    # Interactive mode
    ts.py --filter keyword   # Filter machines
"""

import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

app = typer.Typer(
    help="Tailscale Machine Selector - Copy machine DNS name to clipboard",
    no_args_is_help=False,
)

console = Console()


def is_interactive() -> bool:
    """Check if stdin is a terminal"""
    return sys.stdin.isatty()


def is_wsl() -> bool:
    """Check if running inside WSL"""
    if platform.system() != "Linux":
        return False
    with open("/proc/version", "r") as f:
        return "microsoft" in f.read().lower()


def get_tailscale_command() -> list[str]:
    """Get the appropriate tailscale command for current platform"""
    system = platform.system()

    if system == "Windows":
        possible_paths = [
            Path(os.environ.get("ProgramFiles", "")) / "Tailscale" / "tailscale.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Tailscale" / "tailscale.exe",
        ]
        for path in possible_paths:
            if path.exists():
                return [str(path)]
        return ["tailscale.exe"]

    elif system == "Darwin":
        app_path = Path("/Applications/Tailscale.app/Contents/MacOS/Tailscale")
        if app_path.exists():
            return [str(app_path)]
        return ["tailscale"]

    elif is_wsl():
        return ["tailscale.exe"]

    else:
        return ["tailscale"]


def get_tailscale_machines() -> list[dict]:
    """Get list of Tailscale machines using tailscale status --json"""
    tailscale_cmd = get_tailscale_command()

    try:
        result = subprocess.run(
            tailscale_cmd + ["status", "--json"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            console.print(f"[red]Error: Failed to get Tailscale status[/red]")
            console.print(f"[dim]{result.stderr}[/dim]")
            return []

        data = json.loads(result.stdout)
        peers = data.get("Peer", {})
        self_node = data.get("Self", {})

        machines = []

        if self_node:
            dns_name = self_node.get("DNSName", "").rstrip(".")
            if dns_name:
                machines.append({
                    "name": self_node.get("HostName", ""),
                    "dns_name": dns_name,
                    "online": True,
                    "is_self": True,
                })

        for peer_id, peer in peers.items():
            dns_name = peer.get("DNSName", "").rstrip(".")
            if dns_name:
                machines.append({
                    "name": peer.get("HostName", ""),
                    "dns_name": dns_name,
                    "online": peer.get("Online", False),
                    "is_self": False,
                })

        return machines

    except FileNotFoundError:
        console.print(f"[red]Error: tailscale command not found ({' '.join(tailscale_cmd)})[/red]")
        system = platform.system()
        if system == "Darwin":
            console.print("[yellow]  macOS: brew install tailscale or download from https://tailscale.com/download[/yellow]")
        elif system == "Linux":
            if is_wsl():
                console.print("[yellow]  WSL: Install Tailscale on Windows host[/yellow]")
            else:
                console.print("[yellow]  Linux: https://tailscale.com/download/linux[/yellow]")
        elif system == "Windows":
            console.print("[yellow]  Windows: https://tailscale.com/download/windows[/yellow]")
        return []
    except json.JSONDecodeError as e:
        console.print(f"[red]Error: Failed to parse Tailscale output: {e}[/red]")
        return []


def fzf_select(choices: list[str], prompt: str = "") -> Optional[str]:
    """Use fzf to select from a list of choices"""
    if not choices:
        return None

    fzf_cmd = ["fzf", "--height=60%", "--layout=reverse", "--border", "--ansi"]

    if prompt:
        fzf_cmd.extend(["--header", prompt])

    try:
        process = subprocess.Popen(
            fzf_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        output, error = process.communicate(input="\n".join(choices))

        if process.returncode == 0 and output:
            return output.strip()
        return None

    except FileNotFoundError:
        console.print("[red]Error: fzf not found. Please install fzf first.[/red]")
        console.print("[yellow]  macOS: brew install fzf[/yellow]")
        console.print("[yellow]  Linux: sudo apt install fzf[/yellow]")
        return None
    except Exception as e:
        console.print(f"[red]fzf error: {e}[/red]")
        return None


def copy_to_clipboard(text: str) -> bool:
    """Copy text to clipboard"""
    system = platform.system()

    try:
        if system == "Darwin":
            subprocess.run(["pbcopy"], input=text, text=True, check=True)
        elif system == "Linux":
            if is_wsl():
                subprocess.run(["clip.exe"], input=text, text=True, check=True)
            else:
                try:
                    subprocess.run(
                        ["xclip", "-selection", "clipboard"],
                        input=text,
                        text=True,
                        check=True,
                    )
                except FileNotFoundError:
                    subprocess.run(
                        ["xsel", "--clipboard", "--input"],
                        input=text,
                        text=True,
                        check=True,
                    )
        elif system == "Windows":
            subprocess.run(["clip"], input=text, text=True, check=True)
        else:
            console.print(f"[yellow]Unsupported platform: {system}[/yellow]")
            return False
        return True
    except FileNotFoundError:
        console.print("[red]Error: Clipboard tool not found[/red]")
        if system == "Linux" and not is_wsl():
            console.print("[yellow]Install xclip: sudo apt install xclip[/yellow]")
        return False
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error copying to clipboard: {e}[/red]")
        return False


@app.command()
def main(
    filter_pattern: Annotated[
        str,
        typer.Option("--filter", "-f", help="Filter machines by name or DNS"),
    ] = "",
    online_only: Annotated[
        bool,
        typer.Option("--online/--all", help="Show only online machines"),
    ] = False,
):
    """Select a Tailscale machine and copy its DNS name to clipboard."""
    if not is_interactive():
        console.print("[red]Error: This tool requires an interactive terminal[/red]")
        raise typer.Exit(1)

    machines = get_tailscale_machines()

    if not machines:
        console.print("[yellow]No Tailscale machines found[/yellow]")
        raise typer.Exit(1)

    if online_only:
        machines = [m for m in machines if m["online"]]

    if filter_pattern:
        machines = [
            m for m in machines
            if filter_pattern.lower() in m["name"].lower()
            or filter_pattern.lower() in m["dns_name"].lower()
        ]

    if not machines:
        console.print("[yellow]No machines match the filter[/yellow]")
        raise typer.Exit(1)

    choices = []
    for m in machines:
        status = "[+]" if m["online"] else "[-]"
        self_marker = " (self)" if m.get("is_self") else ""
        choices.append(f"{status} {m['dns_name']}{self_marker}")

    selected = fzf_select(choices, prompt="Select Tailscale machine")

    if not selected:
        console.print("[yellow]No machine selected[/yellow]")
        raise typer.Exit(0)

    dns_name = selected.split(" ", 1)[1].replace(" (self)", "").strip()

    if copy_to_clipboard(dns_name):
        console.print(f"[green]Copied to clipboard:[/green] {dns_name}")
    else:
        console.print(f"[yellow]DNS name:[/yellow] {dns_name}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
