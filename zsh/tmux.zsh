# Tmux project management

tmuxp() {
    # Special projects configuration
    special_projects=(
        "dotfiles:$HOME/dotfiles"
        "workspaces:$HOME/workspaces"
    )
    
    # Find git repositories by looking for .git directories and getting their parent directories
    projects=$(find $HOME/workspaces -maxdepth 5 -type d -name ".git" -exec dirname {} \; | \
        awk -v home=$HOME '{
            proj_name=substr($0, length(home)+2);
            gsub("/", "-", proj_name);
            print proj_name ":" $0
        }')
    
    # Add special paths
    for special in "${special_projects[@]}"; do
        projects="$projects
$special"
    done

    if [ $# -eq 0 ]; then
        # Create a temporary file to pass projects data to fzf preview
        temp_file=$(mktemp)
        echo "$projects" > "$temp_file"
        
        selected=$(echo "$projects" | cut -d':' -f1 | fzf --height 40% \
            --reverse \
            --prompt="Select project: " \
            --bind="ctrl-j:preview-down,ctrl-k:preview-up" \
            --preview "proj_path=\$(grep '^{}:' '$temp_file' | cut -d: -f2); 
                      echo \"Path: \$proj_path\"; 
                      echo \"\nGit Status:\"; 
                      git -C \"\$proj_path\" status -s 2>/dev/null || echo 'No git repository'")
        
        rm -f "$temp_file"
    else
        selected=$1
    fi

    [ -z "$selected" ] && return

    project_path=$(echo "$projects" | grep "^$selected:" | cut -d':' -f2)

    if [ ! -d "$project_path" ]; then
        echo "Project directory doesn't exist: $project_path"
        return 1
    fi

    pushd "$project_path" > /dev/null

    session_name=$selected

    if ! tmux has-session -t="$session_name" 2> /dev/null; then
        # Handle special projects
        if [ "$selected" = "dotfiles" ]; then
            # Dotfiles project
            tmux new-session -d -s "$session_name"
            tmux rename-window -t "$session_name:1" 'editor'
            tmux send-keys -t "$session_name:1" "cd $project_path && nvim ." Enter
            
            tmux new-window -t "$session_name:2" -n 'shell'
            tmux send-keys -t "$session_name:2" "cd $project_path" Enter

        elif [ "$selected" = "workspaces" ]; then
            # Workspaces project
            tmux new-session -d -s "$session_name"
            tmux rename-window -t "$session_name:1" 'dashboard'
            tmux send-keys -t "$session_name:1" "cd $project_path && echo 'gh dash'" Enter
            
            tmux new-window -t "$session_name:2" -n 'shell'
            tmux send-keys -t "$session_name:2" "cd $project_path" Enter

        # Detect project type based on files
        elif [ -f "$project_path/Makefile" ]; then
            # Node.js project
            tmux new-session -d -s "$session_name"
            tmux rename-window -t "$session_name:1" 'editor'
            tmux send-keys -t "$session_name:1" "cd $project_path && echo 'nvim .'" Enter
            
            tmux new-window -t "$session_name:2" -n 'shell'
            tmux send-keys -t "$session_name:2" "cd $project_path" Enter

            tmux new-window -t "$session_name:3" -n 'run'
            tmux send-keys -t "$session_name:3" "cd $project_path && make help" Enter

        elif [ -f "$project_path/docker-compose.yml" ]; then
            # Docker project
            tmux new-session -d -s "$session_name"
            tmux rename-window -t "$session_name:1" 'editor'
            tmux send-keys -t "$session_name:1" "cd $project_path && echo 'nvim .'" Enter

            tmux new-window -t "$session_name:2" -n 'shell'
            tmux send-keys -t "$session_name:2" "cd $project_path" Enter
            
            tmux new-window -t "$session_name:3" -n 'run'
            tmux send-keys -t "$session_name:3" "cd $project_path && docker compose ps" Enter

        else
            # Generic project
            tmux new-session -d -s "$session_name"
            tmux rename-window -t "$session_name:1" 'editor'
            tmux send-keys -t "$session_name:1" "cd $project_path && echo 'nvim .'" Enter
                
            tmux new-window -t "$session_name:2" -n 'shell'
            tmux send-keys -t "$session_name:2" "cd $project_path" Enter

        fi

        tmux select-window -t "$session_name:1"
    fi

    # Check if we're already inside tmux
    if [ -n "$TMUX" ]; then
        tmux switch-client -t "$session_name"
    else
        tmux attach -t "$session_name"
    fi

    popd > /dev/null
}

# Create IDE layout with fzf selection
ide() {
    layouts="3-bottom-panels:Main + Sidebar + 3 bottom panels
2-bottom-panels:Main + Sidebar + 2 bottom panels
simple-split:Vertical split only
horizontal-split:Horizontal split only"

    if [ $# -eq 0 ]; then
        selected=$(echo "$layouts" | cut -d':' -f1 | fzf --height 40% \
            --reverse \
            --prompt="Select layout: " \
            --preview 'layout_desc=$(echo "$layouts" | grep "^{}:" | cut -d: -f2); echo "$layout_desc"')
    else
        selected=$1
    fi

    [ -z "$selected" ] && return

    case "$selected" in
        "3-bottom-panels")
            tmux split-window -h -l 20%
            tmux select-pane -L
            tmux split-window -v -l 30%
            tmux split-window -h -l 66%
            tmux split-window -h -l 50%
            tmux select-pane -U
            ;;
        "2-bottom-panels")
            tmux split-window -h -l 20%
            tmux select-pane -L
            tmux split-window -v -l 30%
            tmux split-window -h -l 50%
            tmux select-pane -U
            ;;
        "simple-split")
            tmux split-window -v -l 30%
            tmux select-pane -U
            ;;
        "horizontal-split")
            tmux split-window -h -l 50%
            tmux select-pane -L
            ;;
    esac
}

# Tmux aliases
unalias ta 2>/dev/null
ta() {
    session=$(tmux list-sessions -F "#S" | fzf --height 40% --reverse)
    [ -z "$session" ] && return
    
    if [ -n "$TMUX" ]; then
        tmux switch-client -t "$session"
    else
        tmux attach -t "$session"
    fi
}
alias tk='tmux kill-session -t $(tmux list-sessions -F "#S" | fzf --height 40% --reverse)'
alias tl='tmux list-sessions'
alias tp='tmuxp'
