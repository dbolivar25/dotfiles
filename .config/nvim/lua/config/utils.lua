local M = {}

-- Create a namespace for autocommands
function M.augroup(name)
	return vim.api.nvim_create_augroup("lazyvim_" .. name, { clear = true })
end

-- Check if a plugin is available
function M.has(plugin)
	return require("lazy.core.config").spec.plugins[plugin] ~= nil
end

return M
