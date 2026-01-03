# Create a new worktree and branch from within current git directory.
gwtaa() {
  if [[ -z $1 ]]; then
    echo "Usage: gwa [branch name]"
    return 1
  fi

  if [[ -z $1 ]]; then
    echo "Usage: ga [branch name]"
    return 1 # Changed from 'exit' to 'return' for shell functions
  fi

  local branch="$1"
  local gwt_base="$(basename "$PWD")"
  local gwt_path="../${gwt_base}--${branch}"

  git worktree add -b "$branch" "$gwt_path"
  cd "$gwt_path"
}

# Remove worktree and branch from within active worktree directory.
gwtd() {
  if gum confirm "Remove worktree and branch?"; then
    local cwd base branch root

    cwd="$(pwd)"
    worktree="$(basename "$cwd")"

    # split on first `--`
    root="${worktree%%--*}"
    branch="${worktree#*--}"

    # Protect against accidentally nuking a non-worktree directory
    if [[ $root != $worktree ]]; then
      cd "../$root"
      git worktree remove "$worktree" --force
      git branch -D "$branch"
    fi
  fi
}
