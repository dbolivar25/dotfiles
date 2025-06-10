function clauded --wraps=claude --description="Run Claude with the --dangerously-skip-permissions flag"
    claude --dangerously-skip-permissions $argv
end
