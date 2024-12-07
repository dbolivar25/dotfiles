return {
	"folke/snacks.nvim",
	event = "VimEnter",
	opts = {
		dashboard = {
			enabled = true,
			sections = {
				{ section = "header" },
				{ section = "keys", gap = 1, padding = 1 },
				{ section = "startup" },
			},
			preset = {
				header = [[
███╗   ██╗███████╗ ██████╗ ██╗   ██╗██╗███╗   ███╗
████╗  ██║██╔════╝██╔═══██╗██║   ██║██║████╗ ████║
██╔██╗ ██║█████╗  ██║   ██║██║   ██║██║██╔████╔██║
██║╚██╗██║██╔══╝  ██║   ██║╚██╗ ██╔╝██║██║╚██╔╝██║
██║ ╚████║███████╗╚██████╔╝ ╚████╔╝ ██║██║ ╚═╝ ██║
╚═╝  ╚═══╝╚══════╝ ╚═════╝   ╚═══╝  ╚═╝╚═╝     ╚═╝]],
				keys = {
					{ icon = "󰈞 ", key = "f", desc = "Find File", action = ":Telescope find_files" },
					{ icon = "󰈔 ", key = "n", desc = "New File", action = ":ene | startinsert" },
					{ icon = "󰋚 ", key = "r", desc = "Recent Files", action = ":Telescope oldfiles" },
					{ icon = "󰒋 ", key = "g", desc = "Find Text", action = ":Telescope live_grep" },
					{
						icon = "󰒓 ",
						key = "c",
						desc = "Config",
						action = ":Telescope find_files cwd=" .. vim.fn.stdpath("config"),
					},
					{
						icon = "󰦛 ",
						key = "s",
						desc = "Restore Session",
						action = "lua require('persistence').load()",
					},
					{ icon = "󰏓 ", key = "x", desc = "Lazy Extras", action = ":LazyExtras" },
					{ icon = "󰒲 ", key = "l", desc = "Lazy", action = ":Lazy" },
					{ icon = "󰗼 ", key = "q", desc = "Quit", action = ":qa" },
				},
			},
		},
		notifier = {
			enabled = true,
			timeout = 2000,
			-- Match your dashboard's aesthetic
			icons = {
				error = "󰅚 ",
				warn = " ",
				info = "󰋼 ",
				debug = " ",
				trace = "󰁪 ",
			},
			-- Use rounded borders to match modern UI feel
			style = "fancy",
			top_down = true,
			-- Slightly transparent background
			margin = { top = 0, right = 1, bottom = 0 },
			padding = true,
			-- Reasonable size constraints
			width = { min = 40, max = 0.4 },
			height = { min = 1, max = 0.6 },
			-- Modern timestamp format
			date_format = "%H:%M",
		},
	},
	dependencies = {
		"nvim-tree/nvim-web-devicons",
	},
	config = function(_, opts)
		require("snacks").setup(opts)
	end,
}
