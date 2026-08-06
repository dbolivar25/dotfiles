local M = {}

local virtual_text = {
	spacing = 4,
	source = "if_many",
	prefix = "●",
}

function M.virtual_text(level)
	local opts = vim.deepcopy(virtual_text)
	opts.severity = { min = level }
	return opts
end

function M.set_level(level)
	local opts
	if level == 0 then
		opts = false
	else
		opts = M.virtual_text(level)
	end
	vim.diagnostic.config({ virtual_text = opts })
end

return M
