local M = {}

local ns = vim.api.nvim_create_namespace("baml_template")
local patterns = {
	{ open = "{{", close = "}}" },
	{ open = "{%", close = "%}" },
}

function M.setup(bufnr)
	bufnr = bufnr or vim.api.nvim_get_current_buf()
	if bufnr == 0 then
		bufnr = vim.api.nvim_get_current_buf()
	end

	vim.api.nvim_set_hl(0, "BamlTemplateDelimiter", { link = "Comment" })
	vim.api.nvim_set_hl(0, "BamlTemplateContent", {})

	local function apply_highlights()
		if not vim.api.nvim_buf_is_valid(bufnr) then
			return
		end

		vim.api.nvim_buf_clear_namespace(bufnr, ns, 0, -1)

		local lines = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)

		for row, line in ipairs(lines) do
			row = row - 1

			for _, pattern in ipairs(patterns) do
				local pos = 1
				while true do
					local start_pos = line:find(pattern.open, pos, true)
					if not start_pos then
						break
					end

					local end_pos = line:find(pattern.close, start_pos + #pattern.open, true)
					if not end_pos then
						vim.api.nvim_buf_set_extmark(bufnr, ns, row, start_pos - 1, {
							end_col = start_pos - 1 + #pattern.open,
							hl_group = "BamlTemplateDelimiter",
							priority = 1000,
						})
						break
					end

					vim.api.nvim_buf_set_extmark(bufnr, ns, row, start_pos - 1, {
						end_col = start_pos - 1 + #pattern.open,
						hl_group = "BamlTemplateDelimiter",
						priority = 1000,
					})

					if end_pos > start_pos + #pattern.open then
						vim.api.nvim_buf_set_extmark(bufnr, ns, row, start_pos - 1 + #pattern.open, {
							end_col = end_pos - 1,
							hl_group = "Normal",
							priority = 900,
							hl_mode = "replace",
						})
					end

					vim.api.nvim_buf_set_extmark(bufnr, ns, row, end_pos - 1, {
						end_col = end_pos - 1 + #pattern.close,
						hl_group = "BamlTemplateDelimiter",
						priority = 1000,
					})

					pos = end_pos + #pattern.close
				end
			end
		end
	end

	apply_highlights()

	local group = vim.api.nvim_create_augroup("baml_template_" .. bufnr, { clear = true })
	vim.api.nvim_create_autocmd({ "TextChanged", "InsertLeave" }, {
		group = group,
		buffer = bufnr,
		callback = apply_highlights,
	})
end

return M
