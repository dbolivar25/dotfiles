return {
	"folke/snacks.nvim",
	opts = {
		dashboard = {
			enabled = true,
			preset = {
				pick = function(command, opts)
					opts = opts or {}
					if command == "files" then
						return require("fff").find_files(opts)
					elseif command == "live_grep" then
						return require("fff").live_grep(opts)
					end

					return Snacks.picker(command, opts)
				end,
			},
			sections = {
				{},
				{
					section = "terminal",
					cmd = "/opt/homebrew/bin/chafa ~/.config/nvim/assets/yosemite_forest.png --format symbols --symbols sextant --size 60x17 --stretch; sleep .1",
					height = 17,
					padding = 1,
				},
				{ section = "keys", gap = 1, padding = 1 },
				{ section = "startup" },
			},
		},
	},
}
