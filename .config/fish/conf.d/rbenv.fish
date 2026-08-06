# rbenv should run after generic PATH setup in 001-path.fish.
if command -q rbenv
    rbenv init - fish | source
end
