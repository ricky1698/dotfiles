

alias aws='docker run --rm -it -v ~/.aws:/root/.aws -v $(pwd):/aws amazon/aws-cli'

alias ansible='docker run --rm -it -v $(pwd):/ansible -v ~/.ssh:/root/.ssh -v ~/.aws:/root/.aws -v ~/.ansible:/root/.ansible ansible/ansible'

alias terraform='docker run --rm -it -v $(pwd):/terraform -v ~/.aws:/root/.aws -v ~/.terraform:/root/.terraform hashicorp/terraform'