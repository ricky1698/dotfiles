
# go
export PATH="$HOME/go/bin:$PATH"

# fnm
if [ -f "$HOME/.local/share/fnm" ]; then
  export PATH="$HOME/.local/share/fnm:$PATH"
  eval "$(fnm env --use-on-cd)"
fi
if [ -f "/opt/homebrew/bin/fnm" ]; then
  export PATH="/opt/homebrew/bin/fnm:$PATH"
  eval "$(fnm env --use-on-cd)"
fi
if [ -f "/home/linuxbrew/.linuxbrew/bin/fnm" ]; then
  export PATH="/home/linuxbrew/.linuxbrew/bin/fnm:$PATH"
  eval "$(fnm env --use-on-cd)"
fi

# cuda
export PATH="/usr/local/cuda/bin:$PATH"
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/cuda/lib64:/usr/local/cuda/extras/CUPTI/lib64

# jetbrains
export PATH="$HOME/.local/share/JetBrains/Toolbox/scripts:$PATH"

# maven
export M2_HOME='/opt/apache-maven-3.8.8'
export PATH="$M2_HOME/bin:$PATH"

# dotnet
export PATH="$HOME/.dotnet/tools:$HOME/.dotnet:$PATH"

# bun
export PATH="$HOME/.bun/bin:$PATH"
