local map = vim.keymap.set

-- Better window navigation
map("n", "<C-h>", "<C-w>h", { desc = "Go to left window" })
map("n", "<C-j>", "<C-w>j", { desc = "Go to lower window" })
map("n", "<C-k>", "<C-w>k", { desc = "Go to upper window" })
map("n", "<C-l>", "<C-w>l", { desc = "Go to right window" })

-- Diagnostic navigation
local diagnostics = require("config.diagnostics")

local function set_diagnostic_keymap(lhs, level, description)
	map("n", lhs, function()
		diagnostics.set_level(level)
	end, { desc = description })
end

set_diagnostic_keymap("<leader>d0", 0, "Hide inline diagnostics")
set_diagnostic_keymap("<leader>d1", vim.diagnostic.severity.ERROR, "Show inline errors")
set_diagnostic_keymap("<leader>d2", vim.diagnostic.severity.WARN, "Show inline warnings")
set_diagnostic_keymap("<leader>d3", vim.diagnostic.severity.INFO, "Show inline info")
set_diagnostic_keymap("<leader>d4", vim.diagnostic.severity.HINT, "Show all inline diagnostics")

-- Better indenting
map("v", "<", "<gv")
map("v", ">", ">gv")

-- Convert \n to actual newlines
map("n", "<leader>cn", function()
	vim.cmd([[%s/\\n/\r/ge]])
	require("conform").format()
	vim.notify("Converted \\n to newlines", vim.log.levels.INFO)
end, { desc = "Convert \\n to actual newlines" })
