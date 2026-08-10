function venv
    switch $argv[1]
        case activate a
            if test -e .venv/bin/activate.fish
                source .venv/bin/activate.fish
            else
                echo "Virtual environment not found"
            end
        case deactivate d
            deactivate
        case new n
            python3 -m venv .venv
        case remove r
            rm -rf .venv
        case -h --help
            echo "$(set_color --bold --underline)Usage:$(set_color normal) venv <COMMAND>"
            echo ""
            echo "$(set_color --bold --underline)Commands:$(set_color normal)"
            echo "  $(set_color --bold)activate$(set_color normal)    Activate the virtual environment"
            echo "  $(set_color --bold)deactivate$(set_color normal)  Deactivate the virtual environment"
            echo "  $(set_color --bold)new$(set_color normal)         Create a new virtual environment"
            echo "  $(set_color --bold)remove$(set_color normal)      Remove the virtual environment"
            echo ""
            echo "$(set_color --bold --underline)Options:$(set_color normal)"
            echo "  $(set_color --bold) -h, --help$(set_color normal)     Print help"
            echo "  $(set_color --bold) -v, --version$(set_color normal)  Print version"
        case -v --version
            echo "venv 1.0.0"
        case '*'
            echo "$(set_color --bold --underline)Usage:$(set_color normal) venv <COMMAND>"
            echo ""
            echo "$(set_color --bold --underline)Commands:$(set_color normal)"
            echo "  $(set_color --bold)activate$(set_color normal)    Activate the virtual environment"
            echo "  $(set_color --bold)deactivate$(set_color normal)  Deactivate the virtual environment"
            echo "  $(set_color --bold)new$(set_color normal)         Create a new virtual environment"
            echo "  $(set_color --bold)remove$(set_color normal)      Remove the virtual environment"
            echo ""
            echo "$(set_color --bold --underline)Options:$(set_color normal)"
            echo "  $(set_color --bold) -h, --help$(set_color normal)     Print help"
            echo "  $(set_color --bold) -v, --version$(set_color normal)  Print version"
            return 1
    end
end
