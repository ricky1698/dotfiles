
alias dotfiles='cd $HOME/dotfiles'

if [ $(uname) != "Darwin" ]; then
alias pbcopy='xsel --input --clipboard'
alias pbpaste='xsel --output --clipboard'
fi

# k8s
alias kp='export KUBECONFIG=$(fd config ~/.kube/ | fzf-tmux --preview="cat {}")'

# fzf
alias v='nvim'
alias vv='fd --type f --hidden --exclude .git | fzf-tmux --reverse | xargs nvim'
alias d="cd \$(fd -t d | fzf-tmux --reverse)"

# aws
alias ap='export AWS_PROFILE=$(sed -n "s/\[profile \(.*\)\]/\1/gp" ~/.aws/config | fzf-tmux --reverse)'

# aider
alias aider='uvx -p 3.12 --from aider-chat aider'
alias aidc='uvx -p 3.12 --from aider-chat aider --cache-prompts --no-auto-commits --sonnet'
alias aido='uvx -p 3.12 --from aider-chat aider --model ollama/llama3.1:8b --cache-prompts --no-auto-commits'
alias aidr='uvx -p 3.12 --from aider-chat aider --model openrouter/anthropic/claude-3-sonnet --cache-prompts --no-auto-commits'

alias e='exit'