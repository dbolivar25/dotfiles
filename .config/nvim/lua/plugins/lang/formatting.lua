return {
	{
		"stevearc/conform.nvim",
		opts = {
			formatters_by_ft = {
				c = { "clang-format" },
				cpp = { "clang-format" },
				sh = { "shfmt" },
			},
			formatters = {
				["biome-check"] = {
					command = vim.fn.stdpath("data") .. "/mason/bin/biome",
				},
				shfmt = {
					prepend_args = { "-i", "4", "-ci" },
				},
			},
		},
	},
}
