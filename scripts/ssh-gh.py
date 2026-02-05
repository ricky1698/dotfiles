#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.21.1",
#     "rich>=14.0.0",
# ]
# ///

"""
SSH with GitHub Token Tool

SSH into a remote machine with GitHub token automatically exported in the shell environment.

Usage:
    ssh-gh.py                      # Interactive mode - select from SSH config/Tailscale hosts
    ssh-gh.py --host myserver      # Direct SSH to specific host
    ssh-gh.py -H myserver          # Short form
"""

import json
import secrets
import subprocess
import threading
import time
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.prompt import Prompt

app = typer.Typer(
    help="SSH with GitHub Token - SSH into remote machine with gh token in environment",
    no_args_is_help=False,
)
console = Console()

# Prefix to identify Tailscale hosts in the selection list
TAILSCALE_PREFIX = "[TS] "


def parse_ssh_config() -> list[str]:
    """
    Parse ~/.ssh/config and extract Host entries

    Returns: List of host names (excludes wildcards like *)
    """
    ssh_config_path = Path.home() / ".ssh" / "config"

    if not ssh_config_path.exists():
        console.print("[yellow]Warning: ~/.ssh/config not found[/yellow]")
        return []

    hosts = []
    try:
        with open(ssh_config_path, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("Host ") and not line.startswith("Host *"):
                    host = line.split()[1]
                    # Skip wildcards
                    if "*" not in host:
                        hosts.append(host)
    except Exception as e:
        console.print(f"[yellow]Warning: Failed to parse SSH config: {e}[/yellow]")
        return []

    return sorted(set(hosts))


def find_tailscale_binary() -> str | None:
    """Find the Tailscale binary path."""
    candidates = [
        "tailscale",
        "tailscale.exe",
        "/Applications/Tailscale.app/Contents/MacOS/Tailscale",
        "/usr/bin/tailscale",
        "/usr/local/bin/tailscale",
    ]
    for candidate in candidates:
        try:
            subprocess.run([candidate, "version"], capture_output=True, check=True)
            return candidate
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    return None


def get_tailscale_hosts() -> list[str]:
    """Get Tailscale hosts that have SSH enabled (sshHostKeys)."""
    tailscale_bin = find_tailscale_binary()
    if not tailscale_bin:
        return []

    try:
        result = subprocess.run(
            [tailscale_bin, "status", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)
    except subprocess.CalledProcessError:
        console.print("[yellow]Warning: Failed to get Tailscale status[/yellow]")
        return []
    except json.JSONDecodeError:
        console.print("[yellow]Warning: Failed to parse Tailscale status JSON[/yellow]")
        return []

    hosts = []
    for peer_info in data.get("Peer", {}).values():
        ssh_keys = peer_info.get("sshHostKeys")  # note: lowercase 's'
        if ssh_keys:
            dns_name = peer_info.get("DNSName", "").rstrip(".")
            if dns_name:
                hosts.append(dns_name)

    return sorted(hosts)


def get_gh_token() -> str | None:
    """Get GitHub token from gh CLI"""
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        console.print("[red]Error: Failed to get gh token. Please run 'gh auth login' first.[/red]")
        return None
    except FileNotFoundError:
        console.print("[red]Error: gh CLI not found. Please install GitHub CLI first.[/red]")
        return None


def fzf_select(choices: list[str], prompt: str = "") -> str | None:
    """
    Use fzf to select from a list of choices

    Args:
        choices: List of choices to select from
        prompt: Prompt message

    Returns:
        Selected choice or None if cancelled
    """
    if not choices:
        return None

    # Build fzf command
    fzf_cmd = ["fzf", "--height=40%", "--layout=reverse", "--border", "--ansi"]

    if prompt:
        fzf_cmd.extend(["--header", prompt])

    try:
        # Run fzf with choices as input
        process = subprocess.Popen(
            fzf_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Send choices to fzf
        output, error = process.communicate(input="\n".join(choices))

        # Return selected choice (strip newline)
        if process.returncode == 0 and output:
            return output.strip()
        return None

    except FileNotFoundError:
        console.print("[red]Error: fzf not found. Please install fzf first.[/red]")
        console.print("[yellow]  macOS: brew install fzf[/yellow]")
        console.print("[yellow]  Linux: sudo apt install fzf[/yellow]")
        console.print("[yellow]  Windows: scoop install fzf[/yellow]")
        return None
    except Exception as e:
        console.print(f"[red]fzf error: {e}[/red]")
        return None


def prompt_username(default: str = "vscode") -> str:
    """Prompt user for SSH username with a default value."""
    return Prompt.ask("[cyan]Enter SSH username[/cyan]", default=default)


def ssh_with_gh_token(host: str, token: str | None, username: str | None = None):
    """SSH into host, optionally injecting GH_TOKEN via secure FIFO pipe."""
    ssh_target = f"{username}@{host}" if username else host

    if not token:
        console.print(f"[cyan]Connecting to {ssh_target} (plain mode)...[/cyan]")
        try:
            subprocess.run(["ssh", ssh_target])
            console.print("[green]Session closed[/green]")
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted[/yellow]")
        except Exception as e:
            console.print(f"[red]Connection error: {e}[/red]")
        finally:
            console.print("[cyan]Returned to local environment[/cyan]")
        return

    console.print(f"[cyan]Connecting to {ssh_target}...[/cyan]")
    fifo_path = f"/tmp/gh-pipe-{secrets.token_hex(4)}"

    # Create FIFO, load token, set up git credential helper, then spawn shell
    remote_interactive_cmd = (
        f"rm -f {fifo_path} && "
        f"mkfifo {fifo_path} && chmod 600 {fifo_path} && "
        f"export MY_GH_TOKEN=$(cat {fifo_path}) && rm -f {fifo_path} && "
        f"export GIT_CONFIG_COUNT=1 && "
        f"export GIT_CONFIG_KEY_0='credential.helper' && "
        f"export GIT_CONFIG_VALUE_0='!f() {{ echo \"username=x-access-token\"; echo \"password=$MY_GH_TOKEN\"; }}; f' && "
        f"export DISPLAY=:0 && "
        f"echo 'GitHub credentials securely loaded into memory' && "
        f"exec ${{SHELL:-/bin/sh}} -l"
    )

    def inject_token():
        time.sleep(1.2)  # wait for FIFO creation
        try:
            subprocess.run(
                ["ssh", ssh_target, f"cat > {fifo_path}"],
                input=token,
                text=True,
                capture_output=True,
                check=True
            )
        except Exception as e:
            console.print(f"[red]Token injection failed: {e}[/red]")

    threading.Thread(target=inject_token, daemon=True).start()

    try:
        subprocess.run(["ssh", "-t", ssh_target, remote_interactive_cmd])
        console.print("[green]Session closed[/green]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
    except Exception as e:
        console.print(f"[red]Connection error: {e}[/red]")
    finally:
        console.print("[cyan]Returned to local environment[/cyan]")


@app.command()
def main(
    host: Annotated[
        Optional[str],
        typer.Option("--host", "-H", help="SSH host to connect to (interactive selection if not provided)"),
    ] = None,
    plain: Annotated[
        bool,
        typer.Option("--plain", "-p", help="Plain SSH without GitHub token injection"),
    ] = False,
):
    """SSH into a remote machine with GitHub token exported in the shell environment."""
    token = None
    if not plain:
        token = get_gh_token()
        if not token:
            raise typer.Exit(1)

    username = None
    is_tailscale_host = False

    if not host:
        ssh_hosts = parse_ssh_config()
        tailscale_hosts = get_tailscale_hosts()

        all_hosts = []
        all_hosts.extend(ssh_hosts)
        all_hosts.extend(f"{TAILSCALE_PREFIX}{h}" for h in tailscale_hosts)

        if not all_hosts:
            console.print("[red]No hosts found in SSH config or Tailscale[/red]")
            raise typer.Exit(1)

        if ssh_hosts:
            console.print(f"[green]Found {len(ssh_hosts)} hosts in SSH config[/green]")
        if tailscale_hosts:
            console.print(f"[blue]Found {len(tailscale_hosts)} Tailscale SSH hosts[/blue]")

        selected = fzf_select(all_hosts, prompt="Select SSH host to connect")

        if not selected:
            console.print("[yellow]No host selected[/yellow]")
            raise typer.Exit(0)

        if selected.startswith(TAILSCALE_PREFIX):
            host = selected[len(TAILSCALE_PREFIX):]
            is_tailscale_host = True
        else:
            host = selected

    if is_tailscale_host:
        username = prompt_username()

    ssh_with_gh_token(host, token, username)


if __name__ == "__main__":
    app()
