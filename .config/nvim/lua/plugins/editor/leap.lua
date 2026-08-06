return {
	{
		url = "https://codeberg.org/andyg/leap.nvim.git",
		config = function(_, opts)
			local leap = require("leap")
			for key, value in pairs(opts) do
				leap.opts[key] = value
			end

			vim.keymap.set({ "n", "x", "o" }, "s", "<Plug>(leap-forward)", { desc = "Leap Forward" })
			vim.keymap.set({ "n", "x", "o" }, "S", "<Plug>(leap-backward)", { desc = "Leap Backward" })
			vim.keymap.set({ "n", "x", "o" }, "gs", "<Plug>(leap-from-window)", { desc = "Leap from Window" })
		end,
	},
}
