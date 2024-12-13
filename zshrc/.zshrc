# Path to your oh-my-zsh installation.
export ZSH="$HOME/.oh-my-zsh"

ZSH_THEME="moiamond/gozilla"

plugins=(
  ansible
  helm
  kubectl
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

source $HOME/.config/zsh/conda.zsh
source $HOME/.config/zsh/brew.zsh
source $HOME/.config/zsh/nvim.zsh
source $HOME/.config/zsh/fzf.zsh
source $HOME/.config/zsh/myalias.zsh
source $HOME/.config/zsh/gh.zsh
source $HOME/.config/zsh/path.zsh

# cargo
if [ -f "$HOME/.cargo/env" ]; then
  . "$HOME/.cargo/env"
fi

# bat
export MANPAGER="sh -c 'col -bx | bat -l man -p'"

alias gsbp='git status --short --branch | fzf --no-sort --reverse --preview "git diff --color=always {+2} | diff-so-fancy" --bind=ctrl-j:preview-down --bind=ctrl-k:preview-up --preview-window=right:60%:wrap'
function ghpr() {
  GH_FORCE_TTY=100% gh pr list | fzf --ansi --preview 'GH_FORCE_TTY=100% gh pr view {1}' --preview-window down --header-lines 3 | awk '{print $1}' | xargs gh pr checkout
}
function ghis() {
  GH_FORCE_TTY=100% gh issue list | fzf --ansi --preview 'GH_FORCE_TTY=100% gh issue view -c {1}' --preview-window down | awk '{print $1}' | xargs gh issue view -c
}
alias cbr='git branch --sort=-committerdate | fzf --header "Checkout Recent Branch" --preview "git diff {1} --color=always" --pointer="" | xargs git checkout'

[[ ! -f ~/.env ]] || source ~/.env

# Generated for envman. Do not edit.
[ -s "$HOME/.config/envman/load.sh" ] && source "$HOME/.config/envman/load.sh"
