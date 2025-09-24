function mmd
    # Parse arguments
    set input_file $argv[1]
    set format svg
    set theme default

    # Check for format argument
    if test (count $argv) -ge 2
        set format $argv[2]
    end

    # Check for theme argument
    if test (count $argv) -ge 3
        set theme $argv[3]
    end

    # Generate output filename
    set output_file (string replace -r '\.[^.]*$' ".$format" $input_file)

    # Run mmdc with options
    mmdc -i $input_file -o $output_file -t $theme

    # Notify completion
    echo "Created $output_file"
end
