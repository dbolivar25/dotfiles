local root = function()
	return LazyVim.root({ buf = 0 })
end

local cwd = function()
	return assert((vim.uv or vim.loop).cwd())
end

local config = function()
	return vim.fn.stdpath("config")
end

local function files(dir)
	return function()
		require("fff").find_files({ cwd = dir() })
	end
end

local function grep(dir, word)
	return function()
		local fff = require("fff")
		local opts = { cwd = dir() }
		if word then
			fff.live_grep_under_cursor(opts)
		else
			fff.live_grep(opts)
		end
	end
end

local replaced_keys = {
	"<leader><space>",
	"<leader>/",
	"<leader>fc",
	"<leader>ff",
	"<leader>fF",
	"<leader>sg",
	"<leader>sG",
	"<leader>sw",
	"<leader>sW",
}

local function disable_snacks_keys()
	return vim.tbl_map(function(key)
		return { key, false }
	end, replaced_keys)
end

return {
	{
		"folke/snacks.nvim",
		keys = disable_snacks_keys(),
	},
	{
		"dmtrKovalenko/fff.nvim",
		build = function()
			require("fff.download").download_or_build_binary()
		end,
		lazy = false,
		keys = {
			{
				"<leader><space>",
				files(root),
				desc = "Find Files (Root Dir)",
			},
			{
				"<leader>/",
				grep(root),
				desc = "Grep (Root Dir)",
			},
			{
				"<leader>fc",
				files(config),
				desc = "Find Config File",
			},
			{
				"<leader>ff",
				files(root),
				desc = "Find Files (Root Dir)",
			},
			{
				"<leader>fF",
				files(cwd),
				desc = "Find Files (cwd)",
			},
			{
				"<leader>sg",
				grep(root),
				desc = "Grep (Root Dir)",
			},
			{
				"<leader>sG",
				grep(cwd),
				desc = "Grep (cwd)",
			},
			{
				"<leader>sw",
				grep(root, true),
				mode = { "n", "x" },
				desc = "Visual selection or word (Root Dir)",
			},
			{
				"<leader>sW",
				grep(cwd, true),
				mode = { "n", "x" },
				desc = "Visual selection or word (cwd)",
			},
		},
	},
}
