return {
	{
		"f-person/auto-dark-mode.nvim",
		lazy = false,
		opts = {},
	},
	{
		"rose-pine/neovim",
		name = "rose-pine",
		priority = 1000,
		opts = {
			variant = "auto",
			dark_variant = "main",
			dim_inactive_windows = false,
			styles = {
				bold = true,
				italic = true,
				transparency = true,
			},
			highlight_groups = {
				WinBar = { bg = "NONE" },
				WinBarNC = { fg = "muted", bg = "NONE", inherit = false },
			},
		},
	},
	{
		"nvim-lualine/lualine.nvim",
		opts = {
			options = {
				theme = function()
					package.loaded["lualine.themes.rose-pine"] = nil
					local theme = require("lualine.themes.rose-pine")
					for _, mode in pairs(theme) do
						for section, highlight in pairs(mode) do
							-- Keep mode colors readable without their solid backgrounds.
							if section == "a" and highlight.bg ~= "NONE" then
								highlight.fg = highlight.bg
							end
							highlight.bg = "NONE"
						end
					end
					return theme
				end,
			},
		},
	},
	{
		"akinsho/bufferline.nvim",
		opts = {
			highlights = {
				group_label = { bg = "NONE" },
			},
		},
	},
	{
		"LazyVim/LazyVim",
		opts = {
			colorscheme = "rose-pine",
		},
	},
	{ "folke/tokyonight.nvim", enabled = false },
	{ "catppuccin/nvim", enabled = false },
}
