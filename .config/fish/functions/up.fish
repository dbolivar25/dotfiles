function up
    if test (count $argv) -lt 1
        cd ..
    else
        set -l levels $argv[1]
        set -l path (string repeat -n $levels ../)
        cd $path
    end
end
