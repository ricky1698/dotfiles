# Path to your oh-my-zsh installation.
export ZSH="$HOME/.oh-my-zsh"

ZSH_THEME="moiamond/gozilla"

plugins=(
  ansible
  aws
  helm
  kubectl
  kube-ps1
  terraform
  git
  docker
  zsh-syntax-highlighting
  zsh-autosuggestions
)

source $ZSH/oh-my-zsh.sh

# You may need to manually set your language environment
export LANG=en_US.UTF-8
# export LC_ALL="en_US.UTF8"

export XCURSOR_SIZE=32

# User configuration

source $HOME/.config/zsh/path.zsh
source $HOME/.config/zsh/conda.zsh
source $HOME/.config/zsh/brew.zsh
source $HOME/.config/zsh/k8s.zsh
source $HOME/.config/zsh/helm.zsh
source $HOME/.config/zsh/nvim.zsh
source $HOME/.config/zsh/fzf.zsh
source $HOME/.config/zsh/myalias.zsh
source $HOME/.config/zsh/gh.zsh
source $HOME/.config/zsh/git.zsh
source $HOME/.config/zsh/yazi.zsh
#source $HOME/.config/zsh/direnv.zsh
source $HOME/.config/zsh/tmux.zsh
source $HOME/.config/zsh/mise.zsh
source $HOME/.config/zsh/zoxide.zsh
source $HOME/.config/zsh/just.zsh
source $HOME/.config/zsh/make.zsh
source $HOME/.config/zsh/aws.zsh

# cargo
if [ -f "$HOME/.cargo/env" ]; then
  . "$HOME/.cargo/env"
fi

# bat
export MANPAGER="sh -c 'col -bx | bat -l man -p'"

alias gsbp='git status --short --branch | fzf --no-sort --reverse --preview "git diff --color=always {+2} | diff-so-fancy" --bind=ctrl-j:preview-down --bind=ctrl-k:preview-up --preview-window=right:60%:wrap'
alias cbr='git branch --sort=-committerdate | fzf --header "Checkout Recent Branch" --preview "git diff {1} --color=always" --pointer="" | xargs git checkout'

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
# [[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

[[ ! -f ~/.env ]] || source ~/.env

# Generated for envman. Do not edit.
[ -s "$HOME/.config/envman/load.sh" ] && source "$HOME/.config/envman/load.sh"


# Added by LM Studio CLI (lms)
export PATH="$PATH:$HOME/.lmstudio/bin"
# End of LM Studio CLI section

bindkey '^[[1;3D' backward-word  # alt-left
bindkey '^[[1;3C' forward-word   # alt-right

# Added by Antigravity
export PATH="$HOME/.antigravity/antigravity/bin:$PATH"
