
# if direnv is installed, load it
if ! [ -x "$(command -v direnv)" ]; then
    eval "$(direnv hook zsh)"
fi
