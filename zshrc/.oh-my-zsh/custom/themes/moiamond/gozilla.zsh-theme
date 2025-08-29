local return_code="%(?..%{$fg[red]%}%? ↵%{$reset_color%})"

if [[ $UID -eq 0 ]]; then
    local user_host='%{$terminfo[bold]$fg[red]%}%n'
    local user_symbol='#'
else
    local user_host='%{$terminfo[bold]$fg[green]%}%n'
    local user_symbol='$'
fi

local current_host='%{$fg[green]%}[%m% ] %{$reset_color%}'
local current_path='%{$terminfo[bold]$fg[blue]%}%~ %{$reset_color%}'
local current_dir='%{$fg[cyan]%}%c %{$reset_color%}'

local git_branch='%{$fg[yellow]%}$(git_prompt_info) %{$reset_color%}'
local kube_info='$(kube_ps1)'
local aws_info='%{$fg[magenta]%}$(aws_prompt_info) %{$reset_color%}'

# local line_end='%{$fg_bold[blue]%} % %{$reset_color%}'
local line_end='%{$reset_color%}'

PROMPT="${current_host}${current_path} ${aws_info}${kube_info}
╰─➜ ${git_branch}${current_dir}%B${user_symbol}%b "
RPROMPT="%B${return_code}%xb"

ZSH_THEME_GIT_PROMPT_PREFIX="("
ZSH_THEME_GIT_PROMPT_SUFFIX=")"
ZSH_THEME_GIT_PROMPT_DIRTY=""
ZSH_THEME_GIT_PROMPT_CLEAN=""
