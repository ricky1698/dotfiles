#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "rich>=13.7.0",
# ]
# ///

"""
VSCode Remote Access Tool

Unified tool for opening remote workspaces in VSCode via SSH Remote or DevContainer.
Works on Windows (PowerShell), macOS, and Linux.

Usage:
    vsc.py                              # Interactive mode
    vsc.py --host ssh-remote-host       # Select workspace on specific host
    vsc.py --filter ca-expl             # Filter workspaces
    vsc.py --mode devcontainer          # Direct mode selection
    vsc.py --path /full/path            # Open specific path
"""

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console

# Check if running in interactive terminal
def is_interactive() -> bool:
    """Check if stdin is a terminal"""
    return sys.stdin.isatty()

console = Console()


def parse_ssh_config() -> list[str]:
    """
    Parse ~/.ssh/config and extract Host entries

    Returns: List of host names (excludes wildcards like *)
    """
    ssh_config_path = Path.home() / ".ssh" / "config"

    if not ssh_config_path.exists():
        return []

    hosts = []
    try:
        with open(ssh_config_path, "r") as f:
            for line in f:
                line = line.strip()
                # Match "Host hostname" lines, ignore wildcards
                if line.startswith("Host ") and not line.startswith("Host *"):
                    # Extract host name(s) after "Host"
                    parts = line.split()[1:]
                    for host in parts:
                        # Skip wildcard patterns
                        if "*" not in host and "?" not in host:
                            hosts.append(host)
    except Exception as e:
        console.print(f"[yellow]Warning: Failed to parse SSH config: {e}[/yellow]")
        return []

    return sorted(set(hosts))


def ssh_exec(host: str, command: str) -> tuple[str, int]:
    """
    Execute command on remote host via SSH

    Returns: (stdout, exit_code)
    """
    result = subprocess.run(["ssh", host, command], capture_output=True, text=True)
    return result.stdout, result.returncode


def list_remote_directories(host: str, base_path: str, maxdepth: int = 1) -> list[str]:
    """List directories on remote host"""
    cmd = f"find '{base_path}' -maxdepth {maxdepth} -type d 2>/dev/null | sort"
    stdout, exit_code = ssh_exec(host, cmd)

    if exit_code != 0:
        return []

    return [line.strip() for line in stdout.splitlines() if line.strip()]


def has_devcontainer(host: str, path: str) -> bool:
    """Check if directory has devcontainer config"""
    cmd = f"[ -d '{path}/.devcontainer' ] || [ -f '{path}/.devcontainer.json' ] && echo 'yes' || echo 'no'"
    stdout, _ = ssh_exec(host, cmd)
    return stdout.strip() == "yes"


def list_containers(host: str, filter_pattern: str = "") -> list[dict]:
    """List running Docker containers"""
    cmd = "docker ps --format '{{.ID}}\t{{.Names}}\t{{.Image}}'"
    stdout, exit_code = ssh_exec(host, cmd)

    if exit_code != 0:
        return []

    containers = []
    for line in stdout.splitlines():
        if not line.strip():
            continue

        parts = line.strip().split("\t")
        if len(parts) >= 3:
            container_id, name, image = parts[0], parts[1], parts[2]
            if (
                not filter_pattern
                or filter_pattern.lower() in image.lower()
                or filter_pattern.lower() in name.lower()
            ):
                containers.append({"id": container_id, "name": name, "image": image})

    return containers


def fzf_select(
    choices: list[str],
    prompt: str = "",
    preview: Optional[str] = None,
    preview_window: str = "down:40%",
    delimiter: Optional[str] = None,
) -> Optional[str]:
    """
    Use fzf to select from a list of choices

    Args:
        choices: List of choices to select from
        prompt: Prompt message
        preview: Preview command (can use {} as placeholder for selection)
        preview_window: Preview window configuration
        delimiter: Field delimiter (e.g., '\t' for tab-separated values)

    Returns:
        Selected choice or None if cancelled
    """
    if not choices:
        return None

    # Build fzf command
    fzf_cmd = ["fzf", "--height=60%", "--layout=reverse", "--border", "--ansi"]

    if prompt:
        fzf_cmd.extend(["--header", prompt])

    # If delimiter is specified, show only specific fields
    if delimiter:
        fzf_cmd.extend(["--delimiter", delimiter, "--with-nth", "2.."])

    if preview:
        fzf_cmd.extend(["--preview", preview, "--preview-window", preview_window])

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


def get_code_command() -> str:
    """Get the appropriate code command for current platform"""
    if platform.system() == "Windows":
        # Try common locations on Windows
        possible_paths = [
            Path(os.environ.get("LOCALAPPDATA", ""))
            / "Programs"
            / "Microsoft VS Code"
            / "bin"
            / "code.cmd",
            Path(os.environ.get("ProgramFiles", ""))
            / "Microsoft VS Code"
            / "bin"
            / "code.cmd",
        ]

        for path in possible_paths:
            if path.exists():
                return str(path)

        # Fallback to PATH
        return "code.cmd"
    else:
        return "code"


def open_vscode_ssh(host: str, path: str):
    """Open VSCode in SSH Remote mode"""
    console.print(f"[cyan]Opening {path} on {host} in VSCode SSH Remote...[/cyan]")
    code_cmd = get_code_command()
    subprocess.run([code_cmd, "--remote", f"ssh-remote+{host}", path])


def open_vscode_devcontainer(host: str, workspace_path: str, workspace_name: str):
    """Open VSCode in DevContainer mode"""
    console.print(f"[cyan]Opening {workspace_path} on {host} in DevContainer...[/cyan]")

    # Search for running container
    containers = list_containers(host, workspace_name)

    if containers:
        container = containers[0]
        console.print(f"[green]Found running container: {container['name']}[/green]")
        console.print(f"[dim]Image: {container['image'][:60]}...[/dim]")

        # Set DOCKER_HOST for remote Docker
        os.environ["DOCKER_HOST"] = f"ssh://{host}"

        # Encode container configuration to hex
        container_config = f'{{"containerName":"/{container["name"]}"}}'
        hex_config = container_config.encode().hex()

        # DevContainer internal path
        container_path = f"/workspaces/{workspace_name}"

        # Open VSCode
        code_cmd = get_code_command()
        uri = f"vscode-remote://attached-container+{hex_config}{container_path}"
        subprocess.run([code_cmd, "--folder-uri", uri])

        # Clean up environment
        if "DOCKER_HOST" in os.environ:
            del os.environ["DOCKER_HOST"]
    else:
        console.print(
            f"[yellow]No running container found for {workspace_name}[/yellow]"
        )
        console.print(
            "[dim]Opening in SSH Remote (VSCode will prompt to 'Reopen in Container')...[/dim]"
        )
        open_vscode_ssh(host, workspace_path)


def open_terminal(host: str, filter_pattern: str, user: str = "vscode"):
    """Open terminal session in Docker container"""
    containers = list_containers(host, filter_pattern)

    if not containers:
        console.print(
            f"[red]No running containers matching '{filter_pattern}' found on {host}[/red]"
        )
        return

    # Select container
    choices = [f"{c['name']} ({c['image'][:40]}...)" for c in containers]

    selected = fzf_select(choices, prompt="Select container to connect")

    if not selected:
        console.print("[yellow]No container selected[/yellow]")
        return

    # Get selected container ID
    idx = choices.index(selected)
    container = containers[idx]

    console.print(
        f"[cyan]Connecting to container {container['id']} on {host}...[/cyan]"
    )

    # Connect to container
    if platform.system() == "Windows":
        # Use PowerShell SSH
        cmd = f"ssh -t {host} \"docker exec -it -u {user} {container['id']} zsh -c 'source ~/.zshrc; tmux attach || tmux new'\""
        subprocess.run(["powershell", "-Command", cmd])
    else:
        cmd = f"docker exec -it -u {user} {container['id']} zsh -c 'source ~/.zshrc; tmux attach || tmux new'"
        subprocess.run(["ssh", "-t", host, cmd])


def main():
    parser = argparse.ArgumentParser(
        description="VSCode Remote Access Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Remote SSH host (auto-selected in interactive mode)",
    )
    parser.add_argument("--path", help="Workspace path")
    parser.add_argument(
        "--mode", choices=["ssh", "devcontainer", "terminal"], help="Mode"
    )
    parser.add_argument(
        "--filter", default=".", help="Filter for workspace/container search"
    )
    parser.add_argument(
        "--base-path",
        default=None,
        help="Base path for workspaces (auto-detected if not provided)",
    )

    args = parser.parse_args()

    # Step 0: Select host if not provided
    host = args.host

    if not host:
        if is_interactive():
            # Read SSH config and let user select
            hosts = parse_ssh_config()

            if not hosts:
                console.print("[red]No hosts found in ~/.ssh/config[/red]")
                console.print(
                    "[yellow]Please specify --host or add hosts to your SSH config[/yellow]"
                )
                return

            selected_host = fzf_select(hosts, prompt="Select SSH host")

            if not selected_host:
                console.print("[yellow]No host selected[/yellow]")
                return

            host = selected_host.strip()
        else:
            console.print(
                "[red]Error: --host is required in non-interactive mode[/red]"
            )
            return

    # Auto-detect base_path if not provided
    base_path = args.base_path
    if not base_path:
        console.print(f"[dim]Auto-detecting base path on {host}...[/dim]")
        remote_home, exit_code = ssh_exec(host, "echo $HOME")
        if exit_code == 0 and remote_home.strip():
            base_path = f"{remote_home.strip()}/workspaces"
            console.print(f"[dim]Using base path: {base_path}[/dim]")
        else:
            console.print(f"[red]Failed to detect home directory on {host}[/red]")
            return
    else:
        base_path = args.base_path

    # Step 1: Select workspace if not provided
    workspace_path = args.path

    if not workspace_path:
        console.print(f"[cyan]📁 Connecting to {host}...[/cyan]")

        dirs = list_remote_directories(host, base_path, maxdepth=1)

        if args.filter != ".":
            dirs = [d for d in dirs if args.filter.lower() in d.lower()]

        if not dirs:
            console.print(f"[red]No directories found in {base_path} on {host}[/red]")
            return

        # If only one match and mode is specified, auto-select it
        if len(dirs) == 1 and args.mode:
            workspace_path = dirs[0]
            console.print(f"[green]Auto-selected: {workspace_path}[/green]")
        # If not interactive, require exact path or single match
        elif not is_interactive():
            if len(dirs) == 1:
                workspace_path = dirs[0]
                console.print(f"[green]Auto-selected: {workspace_path}[/green]")
            else:
                console.print(
                    f"[red]Error: Multiple matches found in non-interactive mode[/red]"
                )
                console.print(
                    f"[yellow]Found {len(dirs)} directories matching '{args.filter}':[/yellow]"
                )
                for d in dirs:
                    console.print(f"  - {d}")
                console.print(
                    f"\n[yellow]Please specify --path or use a more specific --filter[/yellow]"
                )
                return
        else:
            # Interactive selection - show list immediately without pre-checking
            # devcontainer check happens in fzf preview (lazy evaluation)
            preview_cmd = f"ssh {host} 'ls -lah {{}} && echo && if [ -d {{}}/.devcontainer ] || [ -f {{}}/.devcontainer.json ]; then echo \"✓ DevContainer available\"; fi'"

            selected = fzf_select(
                dirs,
                prompt=f"Select workspace on {host}",
                preview=preview_cmd,
                preview_window="down:40%",
            )

            if not selected:
                console.print("[yellow]No workspace selected[/yellow]")
                return

            workspace_path = selected.strip()

    workspace_name = Path(workspace_path).name

    # Step 2: Select mode if not provided
    mode = args.mode

    if not mode:
        has_dc = has_devcontainer(host, workspace_path)

        mode_choices = []
        mode_map = {}

        if has_dc:
            choice = "devcontainer\tOpen in DevContainer (recommended)"
            mode_choices.append(choice)
            mode_map[choice] = "devcontainer"

        choice_ssh = "ssh\tOpen in SSH Remote"
        mode_choices.append(choice_ssh)
        mode_map[choice_ssh] = "ssh"

        choice_term = "terminal\tOpen Terminal Session"
        mode_choices.append(choice_term)
        mode_map[choice_term] = "terminal"

        selected = fzf_select(
            mode_choices, prompt=f"Select mode for {workspace_name}", delimiter="\t"
        )

        if not selected:
            console.print("[yellow]No mode selected[/yellow]")
            return

        mode = selected.split("\t")[0]

    # Step 3: Execute based on mode
    if mode == "devcontainer":
        open_vscode_devcontainer(host, workspace_path, workspace_name)
    elif mode == "ssh":
        open_vscode_ssh(host, workspace_path)
    elif mode == "terminal":
        open_terminal(host, workspace_name)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
