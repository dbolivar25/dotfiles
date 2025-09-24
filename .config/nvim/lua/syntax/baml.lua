-- BAML Template Interpolation Highlighter
local M = {}

function M.setup()
    local ns = vim.api.nvim_create_namespace("baml_template")

    -- Link to Comment for same gray as other punctuation
    vim.api.nvim_set_hl(0, "BamlTemplateDelimiter", { link = "Comment" })
    -- Clear highlighting for content (use default/normal text color)
    vim.api.nvim_set_hl(0, "BamlTemplateContent", {})

    local function apply_highlights()
        local bufnr = vim.api.nvim_get_current_buf()
        vim.api.nvim_buf_clear_namespace(bufnr, ns, 0, -1)

        local lines = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)

        for row, line in ipairs(lines) do
            row = row - 1

            -- Pattern to match template interpolations
            local patterns = {
                { open = "{{", close = "}}" },
                { open = "{%", close = "%}" },
            }

            for _, pattern in ipairs(patterns) do
                local pos = 1
                while true do
                    -- Find opening delimiter
                    local start_pos = line:find(pattern.open, pos, true)
                    if not start_pos then
                        break
                    end

                    -- Find closing delimiter
                    local end_pos = line:find(pattern.close, start_pos + #pattern.open, true)
                    if not end_pos then
                        -- Just highlight the opening delimiter if no closing found
                        vim.api.nvim_buf_set_extmark(bufnr, ns, row, start_pos - 1, {
                            end_col = start_pos - 1 + #pattern.open,
                            hl_group = "BamlTemplateDelimiter",
                            priority = 1000,
                        })
                        break
                    end

                    -- Highlight opening delimiter
                    vim.api.nvim_buf_set_extmark(bufnr, ns, row, start_pos - 1, {
                        end_col = start_pos - 1 + #pattern.open,
                        hl_group = "BamlTemplateDelimiter",
                        priority = 1000,
                    })

                    -- Override content between delimiters to use default color
                    if end_pos > start_pos + #pattern.open then
                        vim.api.nvim_buf_set_extmark(bufnr, ns, row, start_pos - 1 + #pattern.open, {
                            end_col = end_pos - 1,
                            hl_group = "Normal",
                            priority = 900,
                            hl_mode = "replace",
                        })
                    end

                    -- Highlight closing delimiter
                    vim.api.nvim_buf_set_extmark(bufnr, ns, row, end_pos - 1, {
                        end_col = end_pos - 1 + #pattern.close,
                        hl_group = "BamlTemplateDelimiter",
                        priority = 1000,
                    })

                    -- Move position forward
                    pos = end_pos + #pattern.close
                end
            end
        end
    end

    -- Apply once
    apply_highlights()

    -- Reapply on changes
    vim.api.nvim_create_autocmd({ "TextChanged", "InsertLeave" }, {
        buffer = 0,
        callback = apply_highlights,
    })
end

return M

