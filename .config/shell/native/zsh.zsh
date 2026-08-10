# Shell-native commands that must mutate the calling Zsh process.
load_env() {
  (( $# <= 1 )) || { print -u2 'Usage: load_env [file]'; return 2; }
  local file=${1:-.env} line key value
  [[ -f "$file" ]] || { print -u2 -r -- "load_env: $file: file not found"; return 1; }

  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ '^[[:space:]]*($|#)' ]] && continue
    [[ "$line" == *=* ]] || continue
    key=${line%%=*}
    value=${line#*=}
    [[ "$key" =~ '^[A-Za-z_][A-Za-z0-9_]*$' ]] || {
      print -u2 -r -- "load_env: invalid name: $key"
      return 1
    }
    export "$key=$value"
  done < "$file"
}

mkcd() {
  command mkdir -p -- "$1" && builtin cd -- "$1"
}

up() {
  if (( $# == 0 )); then
    builtin cd -- ..
    return
  fi
  local levels=$1 destination=""
  [[ "$levels" == <-> ]] || return 2
  if (( levels == 0 )); then
    builtin cd
    return
  fi
  while (( levels > 0 )); do
    destination="../$destination"
    (( levels-- ))
  done
  builtin cd -- "$destination"
}

_venv_usage() {
  print -r -- \
    'Usage: venv <COMMAND>' \
    '' \
    'Commands:' \
    '  activate    Activate the virtual environment' \
    '  deactivate  Deactivate the virtual environment' \
    '  new         Create a new virtual environment' \
    '  remove      Remove the virtual environment' \
    '' \
    'Options:' \
    '  -h, --help     Print help' \
    '  -v, --version  Print version'
}

venv() {
  (( $# == 1 )) || { _venv_usage >&2; return 1; }
  case "$1" in
    activate|a)
      [[ -f .venv/bin/activate ]] || { print -u2 'Virtual environment not found'; return 1; }
      source .venv/bin/activate
      ;;
    deactivate|d)
      (( $+functions[deactivate] )) || { print -u2 'No virtual environment is active'; return 1; }
      deactivate
      ;;
    new|n) command python3 -m venv .venv ;;
    remove|r) command rm -rf -- .venv ;;
    -h|--help) _venv_usage ;;
    -v|--version) print -r -- 'venv 1.0.0' ;;
    *) _venv_usage >&2; return 1 ;;
  esac
}
