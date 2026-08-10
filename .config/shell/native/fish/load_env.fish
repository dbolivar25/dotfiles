function load_env
    for line in (cat .env | string split -n '\n' | string match -vr '^#')
        set arr (string split -n -m 1 = $line)
        if test (count $arr) -eq 2
            set -gx $arr[1] $arr[2]
        end
    end
end
