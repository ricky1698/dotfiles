# Tmux project management

tmuxp() {
    # Find git repositories by looking for .git directories and getting their parent directories
    projects=$(find $HOME/workspaces -maxdepth 5 -type d -name ".git" -exec dirname {} \; | \
        awk -v home=$HOME '{
            proj_name=substr($0, length(home)+2);
            gsub("/", "-", proj_name);
            print proj_name ":" $0
        }')

    if [ $# -eq 0 ]; then
        selected=$(echo "$projects" | cut -d':' -f1 | fzf --height 40% \
            --reverse \
            --prompt="Select project: " \
            --preview 'proj_path=$(echo "$projects" | grep "^{}:" | cut -d: -f2); 
                      echo "Path: $proj_path"; 
                      echo "\nGit Status:"; 
                      git -C "$proj_path" status -s')
    else
        selected=$1
    fi

    [ -z "$selected" ] && return

    project_path=$(echo "$projects" | grep "^$selected:" | cut -d':' -f2)

    if [ ! -d "$project_path" ]; then
        echo "Project directory doesn't exist: $project_path"
        return 1
    fi

    session_name=$selected

    if ! tmux has-session -t="$session_name" 2> /dev/null; then
        # Detect project type based on files
        if [ -f "$project_path/Makefile" ]; then
            # Node.js project
            tmux new-session -d -s "$session_name"
            tmux rename-window -t "$session_name:1" 'editor'
            tmux send-keys -t "$session_name:1" "cd $project_path && nvim ." Enter
            
            tmux new-window -t "$session_name:2" -n 'shell'
            tmux send-keys -t "$session_name:2" "cd $project_path" Enter

            tmux new-window -t "$session_name:3" -n 'run'
            tmux send-keys -t "$session_name:3" "cd $project_path && make help" Enter

        elif [ -f "$project_path/docker-compose.yml" ]; then
            # Docker project
            tmux new-session -d -s "$session_name"
            tmux rename-window -t "$session_name:1" 'editor'
            tmux send-keys -t "$session_name:1" "cd $project_path && nvim ." Enter

            tmux new-window -t "$session_name:2" -n 'shell'
            tmux send-keys -t "$session_name:2" "cd $project_path" Enter
            
            tmux new-window -t "$session_name:3" -n 'run'
            tmux send-keys -t "$session_name:3" "cd $project_path && docker compose ps" Enter

        else
            # Generic project
            tmux new-session -d -s "$session_name"
            tmux rename-window -t "$session_name:1" 'editor'
            tmux send-keys -t "$session_name:1" "cd $project_path && nvim ." Enter
                
            tmux new-window -t "$session_name:2" -n 'shell'
            tmux send-keys -t "$session_name:2" "cd $project_path" Enter

        fi

        tmux select-window -t "$session_name:1"
    fi

    tmux attach -t "$session_name"
}

# Tmux aliases
alias ta='tmux attach -t $(tmux list-sessions -F "#S" | fzf --height 40% --reverse)'
alias tk='tmux kill-session -t $(tmux list-sessions -F "#S" | fzf --height 40% --reverse)'
alias tl='tmux list-sessions'
alias tp='tmuxp'
