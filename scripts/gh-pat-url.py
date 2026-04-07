#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "questionary>=2.0.0",
#     "rich>=13.7.0",
# ]
# ///

"""GitHub Fine-grained PAT URL Builder.

Interactive CLI to compose a pre-filled GitHub fine-grained personal access
token creation URL with the desired permissions and metadata.
"""

import subprocess
import sys
from urllib.parse import urlencode

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

# ---------------------------------------------------------------------------
# Permission catalogue
# ---------------------------------------------------------------------------

REPO_PERMISSIONS: dict[str, str] = {
    "actions": "Actions",
    "administration": "Administration",
    "code_scanning_alerts": "Code scanning alerts",
    "codespaces": "Codespaces",
    "commit_statuses": "Commit statuses",
    "contents": "Contents (code, commits, branches)",
    "dependabot_alerts": "Dependabot alerts",
    "dependabot_secrets": "Dependabot secrets",
    "deployments": "Deployments",
    "environments": "Environments",
    "issues": "Issues",
    "merge_queues": "Merge queues",
    "metadata": "Metadata (read-only, always granted)",
    "pages": "Pages",
    "pull_requests": "Pull requests",
    "secret_scanning": "Secret scanning alerts",
    "secrets": "Secrets",
    "security_advisories": "Security advisories",
    "variables": "Variables",
    "webhooks": "Webhooks",
    "workflows": "Workflows",
}

ORG_PERMISSIONS: dict[str, str] = {
    "members": "Members",
    "organization_administration": "Administration",
    "organization_announcement_banners": "Announcement banners",
    "organization_copilot_seat_management": "Copilot seat management",
    "organization_custom_roles": "Custom roles",
    "organization_projects": "Projects",
    "organization_secrets": "Secrets",
    "organization_variables": "Variables",
}

ACCOUNT_PERMISSIONS: dict[str, str] = {
    "email": "Email addresses",
    "followers": "Followers",
    "gpg_keys": "GPG keys",
    "notification": "Notifications",
    "profile": "Profile",
    "ssh_signing_keys": "SSH signing keys",
    "starring": "Starring",
}

PRESETS: dict[str, dict[str, str]] = {
    "Read repo contents": {"contents": "read"},
    "Push to repos": {"contents": "write"},
    "Push + open PRs + trigger workflows": {
        "contents": "write",
        "pull_requests": "write",
        "workflows": "write",
    },
    "Issue management": {"issues": "write", "pull_requests": "read"},
    "CI/CD (Actions + Deployments)": {
        "actions": "write",
        "contents": "read",
        "deployments": "write",
    },
    "Devcontainer (full dev workflow)": {
        "actions": "read",
        "contents": "write",
        "issues": "write",
        "notification": "read",
        "pull_requests": "write",
        "workflows": "write",
    },
    "Dependabot": {
        "contents": "write",
        "dependabot_alerts": "write",
        "dependabot_secrets": "write",
        "pull_requests": "write",
    },
}

BASE_URL = "https://github.com/settings/personal-access-tokens/new"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def ask_basic_info() -> dict[str, str]:
    """Prompt for token name, description, target owner, and expiration."""
    params: dict[str, str] = {}

    name = questionary.text(
        "Token name (≤40 chars):",
        validate=lambda v: len(v) <= 40 or "Must be ≤40 characters",
    ).ask()
    if name is None:
        raise KeyboardInterrupt
    if name:
        params["name"] = name

    description = questionary.text("Description (optional):").ask()
    if description is None:
        raise KeyboardInterrupt
    if description:
        params["description"] = description

    target = questionary.text(
        "Resource owner — user or org slug (leave blank = yourself):"
    ).ask()
    if target is None:
        raise KeyboardInterrupt
    if target:
        params["target_name"] = target

    expires = questionary.text(
        "Expires in days (1-366) or 'none' (leave blank = GitHub default):",
        validate=lambda v: (
            v == ""
            or v.lower() == "none"
            or (v.isdigit() and 1 <= int(v) <= 366)
            or "Enter 1-366, 'none', or leave blank"
        ),
    ).ask()
    if expires is None:
        raise KeyboardInterrupt
    if expires:
        params["expires_in"] = expires.lower()

    return params


def pick_permissions_from_category(
    category_name: str, permissions: dict[str, str]
) -> dict[str, str]:
    """Let user pick permissions from a category and assign access levels."""
    selected = questionary.checkbox(
        f"  {category_name} permissions:",
        choices=[
            questionary.Choice(title=f"{label} ({key})", value=key)
            for key, label in permissions.items()
        ],
    ).ask()
    if selected is None:
        raise KeyboardInterrupt

    result: dict[str, str] = {}
    for perm in selected:
        if perm == "metadata":
            result[perm] = "read"
            continue
        level = questionary.select(
            f"    {permissions[perm]} → access level:",
            choices=["read", "write", "admin"],
        ).ask()
        if level is None:
            raise KeyboardInterrupt
        result[perm] = level

    return result


def ask_permissions() -> dict[str, str]:
    """Prompt user to choose a preset or custom permissions."""
    mode = questionary.select(
        "How would you like to set permissions?",
        choices=["Use a preset", "Custom selection"],
    ).ask()
    if mode is None:
        raise KeyboardInterrupt

    if mode == "Use a preset":
        preset_name = questionary.select(
            "Choose a preset:",
            choices=list(PRESETS.keys()),
        ).ask()
        if preset_name is None:
            raise KeyboardInterrupt
        return dict(PRESETS[preset_name])

    # Custom selection — pick categories first
    categories = questionary.checkbox(
        "Which permission categories?",
        choices=[
            questionary.Choice("Repository", value="repo", checked=True),
            questionary.Choice("Organization", value="org"),
            questionary.Choice("Account", value="account"),
        ],
    ).ask()
    if categories is None:
        raise KeyboardInterrupt

    perms: dict[str, str] = {}
    category_map = {
        "repo": ("Repository", REPO_PERMISSIONS),
        "org": ("Organization", ORG_PERMISSIONS),
        "account": ("Account", ACCOUNT_PERMISSIONS),
    }
    for cat in categories:
        name, catalogue = category_map[cat]
        perms.update(pick_permissions_from_category(name, catalogue))

    return perms


def build_url(params: dict[str, str], permissions: dict[str, str]) -> str:
    """Build the final GitHub URL."""
    query = {**params, **permissions}
    return f"{BASE_URL}?{urlencode(query)}" if query else BASE_URL


def copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard. Returns True on success."""
    try:
        if sys.platform == "darwin":
            subprocess.run(["pbcopy"], input=text.encode(), check=True)
        elif sys.platform == "linux":
            subprocess.run(
                ["xclip", "-selection", "clipboard"],
                input=text.encode(),
                check=True,
            )
        else:
            return False
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False
    return True


def display_summary(
    params: dict[str, str], permissions: dict[str, str], url: str
) -> None:
    """Print a rich summary of the generated URL."""
    # Basic info table
    if params:
        info_table = Table(
            title="Token Info", show_header=True, header_style="bold cyan"
        )
        info_table.add_column("Field", style="bold")
        info_table.add_column("Value")
        field_labels = {
            "name": "Name",
            "description": "Description",
            "target_name": "Resource Owner",
            "expires_in": "Expires In (days)",
        }
        for key, value in params.items():
            info_table.add_row(field_labels.get(key, key), value)
        console.print(info_table)

    # Permissions table
    if permissions:
        perm_table = Table(
            title="Permissions", show_header=True, header_style="bold cyan"
        )
        perm_table.add_column("Permission", style="bold")
        perm_table.add_column("Level")

        level_style = {"read": "green", "write": "yellow", "admin": "red"}
        all_perms = {**REPO_PERMISSIONS, **ORG_PERMISSIONS, **ACCOUNT_PERMISSIONS}
        for key, level in sorted(permissions.items()):
            label = all_perms.get(key, key)
            styled_level = Text(level, style=level_style.get(level, ""))
            perm_table.add_row(label, styled_level)

        console.print(perm_table)

    # URL panel
    console.print()
    console.print(Panel(url, title="[bold green]Generated URL", expand=False))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    console.print()
    console.print(
        Panel(
            "[bold]GitHub Fine-grained PAT URL Builder[/bold]\n"
            "Compose a pre-filled token creation URL with the right permissions.",
            style="blue",
        )
    )

    try:
        params = ask_basic_info()
        permissions = ask_permissions()
    except KeyboardInterrupt:
        console.print("\n[dim]Cancelled.[/dim]")
        sys.exit(0)

    url = build_url(params, permissions)

    console.print()
    display_summary(params, permissions, url)

    if copy_to_clipboard(url):
        console.print("[bold green]✓ Copied to clipboard![/bold green]")
    else:
        console.print("[dim]Clipboard not available — copy the URL above.[/dim]")


if __name__ == "__main__":
    main()
