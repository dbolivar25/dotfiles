function fridge
    xh $argv[1] http://10.211.55.2:42169$argv[2] authorization:@~/AugmentAI/testing_data/augment_api.txt $argv[3..-1]
end
