#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.21.1",
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
    vsc.py --host local                 # Select local workspace
    vsc.py --filter ca-expl             # Filter workspaces
    vsc.py --mode devcontainer          # Direct mode selection
    vsc.py --path /full/path            # Open specific path
"""

import json
import os
import platform
import subprocess
import sys
from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

app = typer.Typer(
    help="VSCode Remote Access Tool - Open remote workspaces via SSH Remote or DevContainer",
    no_args_is_help=False,
)


class Mode(str, Enum):
    """VSCode opening mode"""

    local = "local"
    ssh = "ssh"
    devcontainer = "devcontainer"
    terminal = "terminal"

# Check if running in interactive terminal
def is_interactive() -> bool:
    """Check if stdin is a terminal"""
    return sys.stdin.isatty()

console = Console()


def is_local_host(host: str) -> bool:
    """Check if host refers to local machine"""
    return host in ("local", "localhost", "127.0.0.1", "")


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


def list_local_directories(base_path: str, maxdepth: int = 1, git_only: bool = False) -> list[str]:
    """List directories on local machine, optionally filter for .git directories"""
    if git_only:
        cmd = f"find '{base_path}' -maxdepth {maxdepth} -type d -name .git 2>/dev/null | sed 's|/.git$||' | sort"
    else:
        cmd = f"find '{base_path}' -maxdepth {maxdepth} -type d 2>/dev/null | sort"

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        return []

    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def list_remote_directories(host: str, base_path: str, maxdepth: int = 1, git_only: bool = False) -> list[str]:
    """List directories on remote host, optionally filter for .git directories"""
    if git_only:
        # Find directories containing .git subdirectory
        cmd = f"find '{base_path}' -maxdepth {maxdepth} -type d -name .git 2>/dev/null | sed 's|/.git$||' | sort"
    else:
        cmd = f"find '{base_path}' -maxdepth {maxdepth} -type d 2>/dev/null | sort"

    stdout, exit_code = ssh_exec(host, cmd)

    if exit_code != 0:
        return []

    return [line.strip() for line in stdout.splitlines() if line.strip()]


def list_directories(host: str, base_path: str, maxdepth: int = 1, git_only: bool = False) -> list[str]:
    """List directories on local or remote host"""
    if is_local_host(host):
        return list_local_directories(base_path, maxdepth, git_only)
    else:
        return list_remote_directories(host, base_path, maxdepth, git_only)


def has_devcontainer(host: str, path: str) -> bool:
    """Check if directory has devcontainer config"""
    if is_local_host(host):
        devcontainer_dir = Path(path) / ".devcontainer"
        devcontainer_json = Path(path) / ".devcontainer.json"
        return devcontainer_dir.exists() or devcontainer_json.exists()
    else:
        cmd = f"[ -d '{path}/.devcontainer' ] || [ -f '{path}/.devcontainer.json' ] && echo 'yes' || echo 'no'"
        stdout, _ = ssh_exec(host, cmd)
        return stdout.strip() == "yes"


def get_workspace_folder(host: str, workspace_path: str, workspace_name: str) -> str:
    """Get workspaceFolder from devcontainer.json, fallback to /workspaces/{name}."""
    default_path = f"/workspaces/{workspace_name}"

    config_files = [
        f"{workspace_path}/.devcontainer/devcontainer.json",
        f"{workspace_path}/.devcontainer.json",
    ]

    for config_file in config_files:
        config_content = None

        if is_local_host(host):
            config_path = Path(config_file)
            if config_path.exists():
                config_content = config_path.read_text()
        else:
            cmd = f"cat '{config_file}' 2>/dev/null"
            stdout, exit_code = ssh_exec(host, cmd)
            if exit_code == 0 and stdout.strip():
                config_content = stdout

        if config_content:
            try:
                config = json.loads(config_content)
                if "workspaceFolder" in config:
                    folder = config["workspaceFolder"]
                    console.print(f"[dim]Using workspaceFolder from config: {folder}[/dim]")
                    return folder
            except json.JSONDecodeError:
                continue

    return default_path


def list_containers(host: str, filter_pattern: str = "") -> list[dict]:
    """List running Docker containers"""
    cmd = "docker ps --format '{{.ID}}\t{{.Names}}\t{{.Image}}'"

    if is_local_host(host):
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        stdout = result.stdout
        exit_code = result.returncode
    else:
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


def is_wsl() -> bool:
    """Check if running inside WSL"""
    if platform.system() != "Linux":
        return False
    with open("/proc/version", "r") as f:
        return "microsoft" in f.read().lower()


def get_code_command() -> str:
    """Get the appropriate code command for current platform"""
    if platform.system() == "Windows":
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
        return "code.cmd"

    if is_wsl():
        # Use Windows code.exe to avoid WSL remote conflict
        return "code.exe"

    return "code"


def open_vscode_local(path: str):
    """Open VSCode locally"""
    console.print(f"[cyan]Opening {path} in VSCode...[/cyan]")
    code_cmd = get_code_command()
    subprocess.run([code_cmd, path])


def open_vscode_ssh(host: str, path: str):
    """Open VSCode in SSH Remote mode"""
    console.print(f"[cyan]Opening {path} on {host} in VSCode SSH Remote...[/cyan]")
    code_cmd = get_code_command()
    subprocess.run([code_cmd, "--remote", f"ssh-remote+{host}", path])


def open_vscode_devcontainer(host: str, workspace_path: str, workspace_name: str):
    """Open VSCode in DevContainer mode"""
    is_local = is_local_host(host)
    location = "local" if is_local else host
    console.print(f"[cyan]Opening {workspace_path} on {location} in DevContainer...[/cyan]")

    # Search for running container
    containers = list_containers(host, workspace_name)

    if containers:
        container = containers[0]
        console.print(f"[green]Found running container: {container['name']}[/green]")
        console.print(f"[dim]Image: {container['image'][:60]}...[/dim]")

        # Encode container configuration to hex
        container_config = f'{{"containerName":"/{container["name"]}"}}'
        hex_config = container_config.encode().hex()

        # Get workspaceFolder from devcontainer.json (or use default)
        container_path = get_workspace_folder(host, workspace_path, workspace_name)

        # Open VSCode
        code_cmd = get_code_command()
        uri = f"vscode-remote://attached-container+{hex_config}{container_path}"

        if not is_local:
            # Set DOCKER_HOST for remote Docker
            os.environ["DOCKER_HOST"] = f"ssh://{host}"

        subprocess.run([code_cmd, "--folder-uri", uri])

        # Clean up environment
        if "DOCKER_HOST" in os.environ:
            del os.environ["DOCKER_HOST"]
    else:
        console.print(
            f"[yellow]No running container found for {workspace_name}[/yellow]"
        )
        if is_local:
            console.print(
                "[dim]Opening locally (VSCode will prompt to 'Reopen in Container')...[/dim]"
            )
            open_vscode_local(workspace_path)
        else:
            console.print(
                "[dim]Opening in SSH Remote (VSCode will prompt to 'Reopen in Container')...[/dim]"
            )
            open_vscode_ssh(host, workspace_path)


def open_terminal(host: str, workspace_name: str, user: str = "vscode"):
    """Open terminal session in Docker container for the workspace"""
    is_local = is_local_host(host)
    location = "locally" if is_local else f"on {host}"
    containers = list_containers(host, workspace_name)

    if not containers:
        console.print(
            f"[red]No running containers matching '{workspace_name}' found {location}[/red]"
        )
        return

    # Auto-select if only one container matches
    if len(containers) == 1:
        container = containers[0]
        console.print(f"[green]Found container: {container['name']}[/green]")
    else:
        # Multiple containers found, let user select
        console.print(f"[yellow]Found {len(containers)} containers matching '{workspace_name}'[/yellow]")
        choices = [f"{c['name']} ({c['image'][:40]}...)" for c in containers]

        selected = fzf_select(choices, prompt="Select container to connect")

        if not selected:
            console.print("[yellow]No container selected[/yellow]")
            return

        idx = choices.index(selected)
        container = containers[idx]

    console.print(
        f"[cyan]Connecting to container {container['id']} {location}...[/cyan]"
    )

    # Connect to container
    exec_cmd = f"docker exec -it -u {user} {container['id']} zsh -c 'source ~/.zshrc; tmux attach || tmux new'"

    if is_local:
        subprocess.run(exec_cmd, shell=True)
    elif platform.system() == "Windows":
        # Use PowerShell SSH
        cmd = f"ssh -t {host} \"{exec_cmd}\""
        subprocess.run(["powershell", "-Command", cmd])
    else:
        subprocess.run(["ssh", "-t", host, exec_cmd])


@app.command()
def main(
    host: Annotated[
        Optional[str],
        typer.Option("--host", "-H", help="Remote SSH host or 'local' for local machine"),
    ] = None,
    path: Annotated[
        Optional[str],
        typer.Option("--path", "-p", help="Workspace path"),
    ] = None,
    mode: Annotated[
        Optional[Mode],
        typer.Option("--mode", "-m", help="Opening mode"),
    ] = None,
    filter_pattern: Annotated[
        str,
        typer.Option("--filter", "-f", help="Filter for workspace/container search"),
    ] = ".",
    base_path: Annotated[
        Optional[str],
        typer.Option("--base-path", "-b", help="Base path for workspaces (auto-detected if not provided)"),
    ] = None,
    depth: Annotated[
        int,
        typer.Option("--depth", "-d", help="Search depth for directories"),
    ] = 4,
    git_only: Annotated[
        bool,
        typer.Option("--git-only/--no-git-only", help="Only show directories containing .git"),
    ] = True,
):
    """Open remote workspaces in VSCode via SSH Remote or DevContainer."""
    # Step 0: Select host if not provided
    selected_host = host

    if not selected_host:
        if is_interactive():
            # Read SSH config and let user select, add "local" option
            hosts = ["local"] + parse_ssh_config()

            if len(hosts) == 1:  # Only "local" available
                console.print("[yellow]No remote hosts found in ~/.ssh/config[/yellow]")

            selected_host = fzf_select(hosts, prompt="Select host (local or SSH)")

            if not selected_host:
                console.print("[yellow]No host selected[/yellow]")
                raise typer.Exit(0)

            selected_host = selected_host.strip()
        else:
            console.print(
                "[red]Error: --host is required in non-interactive mode[/red]"
            )
            raise typer.Exit(1)

    is_local = is_local_host(selected_host)

    # Auto-detect base_path if not provided
    resolved_base_path = base_path
    if not resolved_base_path:
        if is_local:
            resolved_base_path = f"{Path.home()}/workspaces"
            console.print(f"[dim]Using base path: {resolved_base_path}[/dim]")
        else:
            console.print(f"[dim]Auto-detecting base path on {selected_host}...[/dim]")
            remote_home, exit_code = ssh_exec(selected_host, "echo $HOME")
            if exit_code == 0 and remote_home.strip():
                resolved_base_path = f"{remote_home.strip()}/workspaces"
                console.print(f"[dim]Using base path: {resolved_base_path}[/dim]")
            else:
                console.print(f"[red]Failed to detect home directory on {selected_host}[/red]")
                raise typer.Exit(1)

    # Step 1: Select workspace if not provided
    workspace_path = path
    location = "local" if is_local else selected_host

    if not workspace_path:
        console.print(f"[cyan]📁 Selecting workspace on {location}...[/cyan]")

        dirs = list_directories(selected_host, resolved_base_path, maxdepth=depth, git_only=git_only)

        if filter_pattern != ".":
            dirs = [d for d in dirs if filter_pattern.lower() in d.lower()]

        if not dirs:
            console.print(f"[red]No directories found in {resolved_base_path} on {location}[/red]")
            raise typer.Exit(1)

        # If only one match and mode is specified, auto-select it
        if len(dirs) == 1 and mode:
            workspace_path = dirs[0]
            console.print(f"[green]Auto-selected: {workspace_path}[/green]")
        # If not interactive, require exact path or single match
        elif not is_interactive():
            if len(dirs) == 1:
                workspace_path = dirs[0]
                console.print(f"[green]Auto-selected: {workspace_path}[/green]")
            else:
                console.print(
                    "[red]Error: Multiple matches found in non-interactive mode[/red]"
                )
                console.print(
                    f"[yellow]Found {len(dirs)} directories matching '{filter_pattern}':[/yellow]"
                )
                for d in dirs:
                    console.print(f"  - {d}")
                console.print(
                    "\n[yellow]Please specify --path or use a more specific --filter[/yellow]"
                )
                raise typer.Exit(1)
        else:
            # Interactive selection - show list immediately without pre-checking
            # devcontainer check happens in fzf preview (lazy evaluation)
            if is_local:
                preview_cmd = "if [ -d {}/.devcontainer ] || [ -f {}/.devcontainer.json ]; then echo '✓ DevContainer available'; else echo '✗ No DevContainer'; fi && echo && ls -lah {}"
            elif platform.system() == "Windows":
                # Show devcontainer status first, then always show ls (use & instead of &&)
                preview_cmd = f"ssh {selected_host} test -d {{}}/.devcontainer && echo [DevContainer:Yes] || echo [DevContainer:No] & ssh {selected_host} ls -lah {{}}"
            else:
                preview_cmd = f"ssh {selected_host} 'if [ -d {{}}/.devcontainer ] || [ -f {{}}/.devcontainer.json ]; then echo \"✓ DevContainer available\"; else echo \"✗ No DevContainer\"; fi && echo && ls -lah {{}}'"

            selected = fzf_select(
                dirs,
                prompt=f"Select workspace on {location}",
                preview=preview_cmd,
                preview_window="down:40%",
            )

            if not selected:
                console.print("[yellow]No workspace selected[/yellow]")
                raise typer.Exit(0)

            workspace_path = selected.strip()

    workspace_name = Path(workspace_path).name

    # Step 2: Select mode if not provided
    selected_mode = mode.value if mode else None

    if not selected_mode:
        has_dc = has_devcontainer(selected_host, workspace_path)

        mode_choices = []

        if has_dc:
            mode_choices.append("devcontainer\tOpen in DevContainer (recommended)")

        if is_local:
            mode_choices.append("local\tOpen in VSCode (local)")
        else:
            mode_choices.append("ssh\tOpen in SSH Remote")

        mode_choices.append("terminal\tOpen Terminal Session")

        selected = fzf_select(
            mode_choices, prompt=f"Select mode for {workspace_name}", delimiter="\t"
        )

        if not selected:
            console.print("[yellow]No mode selected[/yellow]")
            raise typer.Exit(0)

        selected_mode = selected.split("\t")[0]

    # Step 3: Execute based on mode
    if selected_mode == "devcontainer":
        open_vscode_devcontainer(selected_host, workspace_path, workspace_name)
    elif selected_mode == "local":
        open_vscode_local(workspace_path)
    elif selected_mode == "ssh":
        open_vscode_ssh(selected_host, workspace_path)
    elif selected_mode == "terminal":
        open_terminal(selected_host, workspace_name)


if __name__ == "__main__":
    app()
