# local bin
export PATH="$HOME/.local/bin:$PATH"

# go
export PATH="$HOME/go/bin:$PATH"

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
# bun completions
[ -s "$HOME/.bun/_bun" ] && source "$HOME/.bun/_bun"

# Windsurf
export PATH="$HOME/.codeium/windsurf/bin:$PATH"

# lmstudio
export PATH="$PATH:$HOME/.lmstudio/bin"

# pve-manager
export PATH="$PATH:$HOME/.config/pve-manager/bin"

# rancher desktop
export PATH="$PATH:$HOME/.rd/bin"

# helper
export PATH="$HOME/.config/helper:$PATH"

# Added by get-aspire-cli.sh
export PATH="$HOME/.aspire/bin:$PATH"

# Added by Antigravity
export PATH="$HOME/.antigravity/antigravity/bin:$PATH"
