local function augroup(name)
	return vim.api.nvim_create_augroup("lazyvim_" .. name, { clear = true })
end

-- Auto-formatting
vim.api.nvim_create_autocmd("FileType", {
	group = augroup("formatting"),
	pattern = { "ruby" },
	callback = function()
		vim.b.autoformat = false
	end,
})
