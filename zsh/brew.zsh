if [ $(uname) != "Darwin" ]; then
  if command -v /home/linuxbrew/.linuxbrew/bin/brew >/dev/null 2>&1; then
    eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
  fi
fi
if [ $(uname) = "Darwin" ]; then
 eval $(/opt/homebrew/bin/brew shellenv)
fi