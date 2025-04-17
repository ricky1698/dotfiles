
alias .f='cd $HOME/dotfiles'
alias tmp='cd /tmp'


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

# llm
alias llm='uvx -p 3.12 llm'

alias e='exit'

# ssh ws75
alias ssh-ws75='ssh -i ~/.ssh/rh-ws75'

# fabric
alias fb='fabric'
alias fbc1s='fabric -s -m gpt-4.1-nano -p'
alias fbc2s='fabric -s -m gpt-4.1-mini -p'
alias fbc3s='fabric -s -m anthropic/claude-3.7-sonnet -p'
alias fbr1s='fabric -s -m openai/o3-mini -p'
alias fbr2s='fabric -s -m openai/o3-mini-high -p'
alias fbr3s='fabric -s -m gemini-2.5-pro-exp-03-25 -p'

# paic
alias paic='uvx -p 3.12 --from paic_patterns paic'

# gitingest
alias gitingest='uvx -p 3.12 gitingest'

# yt-dlp
alias yt-dlp='uvx -p 3.12 yt-dlp'

# claude
alias claude='bunx @anthropic-ai/claude-code'

# repomix
alias repomix='bunx repomix'

# brew update && brew outdated && brew upgrade && brew cleanup
alias bubu='brew update && brew outdated && brew upgrade && brew cleanup'

