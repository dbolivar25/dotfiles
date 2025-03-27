# Basic abbreviations
abbr --add vim nvim
abbr --add vi nvim
abbr --add python python3
abbr --add omp oh-my-posh

# ls abbreviations
abbr --add l. 'l -a'
abbr --add ls 'ls -l'
abbr --add la 'ls -la'
abbr --add lD 'ls -lD'
abbr --add lf 'ls -lf'
abbr --add laD 'ls -lDa'
abbr --add laf 'ls -lfa'
abbr --add ll 'll -l'
abbr --add lla 'll -la'
abbr --add llD 'll -lD'
abbr --add llf 'll -lf'
abbr --add llaD 'll -lDa'
abbr --add llaf 'll -lfa'
abbr --add lT 'lt --level'

# Git abbreviations
abbr --add gg lazygit
abbr --add gst 'git status'
abbr --add gdf 'git diff'
abbr --add gad 'git add'
abbr --add gcm 'git commit'
abbr --add gbr 'git branch'
abbr --add gsw 'git switch'
abbr --add grs 'git restore'
abbr --add gpl 'git pull'
abbr --add gplr 'git pull --rebase'
abbr --add gpsh 'git push'
abbr --add gmr 'git merge'

# Docker abbreviations
abbr --add lzd lazydocker
abbr --add dkr docker
abbr --add dkrc 'docker compose'

# Kubernetes abbreviations
abbr --add ktl kubectl
abbr --add ktlg 'kubectl get'
abbr --add ktll 'kubectl logs'
abbr --add ktla 'kubectl apply -f'
abbr --add ktld 'kubectl delete'
abbr --add ktls 'kubectl scale'
abbr --add ktlx 'kubectl exec'

# Rust abbreviations
abbr --add cgr 'cargo run'
abbr --add cgrb 'cargo run --bin'
abbr --add cgrr 'cargo run --release'
abbr --add cgrrb 'cargo run --release --bin'
abbr --add cgt 'cargo test'
abbr --add cgb 'cargo build'
abbr --add cgbb 'cargo build --bin'
abbr --add cgbr 'cargo build --release'
abbr --add cgbrb 'cargo build --release --bin'

# Rust abbreviations with pavex
abbr --add cxr 'cargo px run'
abbr --add cxrr 'cargo px run --release'
abbr --add cxt 'cargo px test'
abbr --add cxb 'cargo px build'
abbr --add cxbr 'cargo px build --release'

# Rust abbreviations with lambda
abbr --add clr 'cargo lambda run'
abbr --add clrr 'cargo lambda run --release'
abbr --add clt 'cargo lambda test'
abbr --add clb 'cargo lambda build'
abbr --add clbr 'cargo lambda build --release'

# OCaml abbreviations
abbr --add op opam
abbr --add dn dune
abbr --add mg mirage
abbr --add dni 'dune init project'
abbr --add ocx 'opam exec -- dune exec'
abbr --add mgc 'mirage configure -t unix'

# Openstack abbreviations
abbr --add os openstack

# Utility abbreviations
abbr --add mkd mkdir
abbr --add x exec
abbr --add j just
abbr --add jj "just --justfile ~/.config/just/justfile --working-directory ."
abbr --add ff fastfetch
abbr --add man batman
abbr --add rc 'pushd ~/.config/fish && nvim && popd'
abbr --add nrc 'pushd ~/.config/nvim && nvim && popd'
abbr --add trc 'pushd ~/.config/ghostty && nvim && popd'
abbr --add src 'pushd ~/.ssh && nvim && popd'
abbr --add arc 'pushd ~/.aws && nvim && popd'
abbr --add cinema asciinema
abbr --add md docling
abbr --add trs 'tmux rename-session'
abbr --add fenv 'env | rg'
abbr --add py python3
abbr --add ipy ipython
