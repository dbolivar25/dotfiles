# Caller-state functions shared by Bash and Zsh.
load_env() {
  [ "$#" -le 1 ] || { printf 'Usage: load_env [file]\n' >&2; return 2; }
  local file=${1:-.env} line trimmed key value
  [ -f "$file" ] || { printf 'load_env: %s: file not found\n' "$file" >&2; return 1; }

  while IFS= read -r line || [ -n "$line" ]; do
    trimmed=${line#"${line%%[![:space:]]*}"}
    case "$trimmed" in
      ""|\#*) continue ;;
    esac
    case "$line" in
      *=*) ;;
      *) continue ;;
    esac
    key=${line%%=*}
    value=${line#*=}
    case "$key" in
      ""|[0-9]*|*[!A-Za-z0-9_]*)
        printf 'load_env: invalid name: %s\n' "$key" >&2
        return 1
        ;;
    esac
    export "$key=$value"
  done < "$file"
}

mkcd() {
  command mkdir -p -- "$1" && builtin cd -- "$1"
}

up() {
  if [ "$#" -eq 0 ]; then
    builtin cd -- ..
    return
  fi
  local levels=$1 destination=""
  case "$levels" in
    ""|*[!0-9]*) return 2 ;;
  esac
  levels=$((10#$levels))
  if [ "$levels" -eq 0 ]; then
    builtin cd
    return
  fi
  while [ "$levels" -gt 0 ]; do
    destination="../$destination"
    levels=$((levels - 1))
  done
  builtin cd -- "$destination"
}

_venv_usage() {
  printf '%s\n' \
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
  [ "$#" -eq 1 ] || { _venv_usage >&2; return 1; }
  case "$1" in
    activate|a)
      [ -f .venv/bin/activate ] || { printf 'Virtual environment not found\n' >&2; return 1; }
      . .venv/bin/activate
      ;;
    deactivate|d)
      command -v deactivate >/dev/null 2>&1 || { printf 'No virtual environment is active\n' >&2; return 1; }
      deactivate
      ;;
    new|n) command python3 -m venv .venv ;;
    remove|r) command rm -rf -- .venv ;;
    -h|--help) _venv_usage ;;
    -v|--version) printf 'venv 1.0.0\n' ;;
    *) _venv_usage >&2; return 1 ;;
  esac
}
