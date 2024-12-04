return {
	{
		"michaelrommel/nvim-silicon",
		cmd = "Silicon",
		config = function()
			require("silicon").setup({
				font = "JetBrainsMono Nerd Font=14",
				theme = "rose-pine",
				background = "#191724",
				pad_horiz = 50,
				pad_vert = 40,
				no_round_corner = false,
				window_title = function()
					return vim.fn.fnamemodify(vim.api.nvim_buf_get_name(0), ":t")
				end,
			})
		end,
	},
}
