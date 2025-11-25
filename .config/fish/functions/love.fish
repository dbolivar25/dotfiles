function love --description "Opens the love game engine"
    if test -f /Applications/love.app/Contents/MacOS/love
        /Applications/love.app/Contents/MacOS/love $argv
    else
        echo "Could not find love.app"
    end
end
