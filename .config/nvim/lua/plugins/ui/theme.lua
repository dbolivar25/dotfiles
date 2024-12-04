return {
	{
		"rose-pine/neovim",
		name = "rose-pine",
		priority = 1000,
		opts = {
			variant = "main",
			dark_variant = "main",
			dim_inactive_windows = true,
			styles = {
				bold = true,
				italic = true,
				transparency = false,
			},
		},
	},
	{
		"LazyVim/LazyVim",
		opts = {
			colorscheme = "rose-pine",
		},
	},
}
