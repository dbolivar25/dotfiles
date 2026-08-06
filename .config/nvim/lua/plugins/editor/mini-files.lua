return {
	{
		"nvim-mini/mini.files",
		lazy = false,
		opts = {
			options = {
				use_as_default_explorer = true,
			},
		},
		keys = {
			{
				"<leader>e",
				function()
					require("mini.files").open(LazyVim.root(), true)
				end,
				desc = "Explorer (Root Directory)",
			},
			{
				"<leader>E",
				function()
					require("mini.files").open(vim.uv.cwd(), true)
				end,
				desc = "Explorer (cwd)",
			},
		},
	},
	{ "nvim-neo-tree/neo-tree.nvim", enabled = false },
}
