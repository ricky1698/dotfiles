#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "rich>=13.7.0",
# ]
# ///

"""
SSH with GitHub Token Tool

SSH into a remote machine with GitHub token automatically exported in the shell environment.

Usage:
    ssh-gh.py                    # Interactive mode - select from SSH config hosts
    ssh-gh.py --host myserver    # Direct SSH to specific host
"""

import argparse
import secrets
import subprocess
import sys
import threading
import time
from pathlib import Path

from rich.console import Console

console = Console()


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


def ssh_with_gh_token(host: str, token: str):
    """
    SSH into host with GH_TOKEN configured in environment using secure FIFO pipe
    
    Uses GIT_CONFIG_* environment variables for credential helper
    with proper username=x-access-token format.
    """
    console.print(f"[cyan]Connecting to {host}...[/cyan]")
    
    # Generate random FIFO path on remote host
    fifo_path = f"/tmp/gh-pipe-{secrets.token_hex(4)}"
    
    # Remote command that creates FIFO, loads token from it, and sets up git credentials
    remote_interactive_cmd = (
        f"mkfifo {fifo_path} && chmod 600 {fifo_path} && "
        f"export MY_GH_TOKEN=$(cat {fifo_path}) && rm {fifo_path} && "
        f"export GIT_CONFIG_COUNT=1 && "
        f"export GIT_CONFIG_KEY_0='credential.helper' && "
        f"export GIT_CONFIG_VALUE_0='!f() {{ echo \"username=x-access-token\"; echo \"password=$MY_GH_TOKEN\"; }}; f' && "
        f"export DISPLAY=:0 && "
        f"echo 'GitHub credentials securely loaded into memory' && "
        f"exec ${{SHELL:-/bin/sh}} -l"
    )
    
    # Background thread to inject token through separate SSH tunnel
    def inject_token():
        # Give main connection time to create FIFO
        time.sleep(1.2)
        try:
            # Send token via stdin to avoid command line exposure
            subprocess.run(
                ["ssh", host, f"cat > {fifo_path}"],
                input=token,
                text=True,
                capture_output=True,
                check=True
            )
        except Exception as e:
            # Silent failure - main connection will timeout if this fails
            console.print(f"[red]Token injection failed: {e}[/red]")
    
    # Start token injection in background
    threading.Thread(target=inject_token, daemon=True).start()
    
    # Launch interactive SSH session
    try:
        subprocess.run(["ssh", "-t", host, remote_interactive_cmd])
        console.print("[green]Session closed[/green]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
    except Exception as e:
        console.print(f"[red]Connection error: {e}[/red]")
    finally:
        console.print("[cyan]Returned to local environment[/cyan]")


def main():
    parser = argparse.ArgumentParser(
        description="SSH with GitHub Token - SSH into remote machine with gh token in environment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--host",
        help="SSH host to connect to (interactive selection if not provided)",
    )

    args = parser.parse_args()

    # Get GitHub token first
    token = get_gh_token()
    if not token:
        sys.exit(1)

    # Select host
    host = args.host

    if not host:
        # Interactive mode - parse SSH config and select
        hosts = parse_ssh_config()
        
        if not hosts:
            console.print("[red]No hosts found in SSH config[/red]")
            sys.exit(1)

        console.print(f"[green]Found {len(hosts)} hosts in SSH config[/green]")
        
        host = fzf_select(hosts, prompt="Select SSH host to connect")
        
        if not host:
            console.print("[yellow]No host selected[/yellow]")
            sys.exit(0)

    # SSH with token
    ssh_with_gh_token(host, token)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
