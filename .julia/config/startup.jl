using Pkg
using Revise

atreplinit() do repl
  Pkg.instantiate()
end
