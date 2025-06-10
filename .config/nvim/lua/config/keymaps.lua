local map = vim.keymap.set

-- Better window navigation
map("n", "<C-h>", "<C-w>h", { desc = "Go to left window" })
map("n", "<C-j>", "<C-w>j", { desc = "Go to lower window" })
map("n", "<C-k>", "<C-w>k", { desc = "Go to upper window" })
map("n", "<C-l>", "<C-w>l", { desc = "Go to right window" })

-- Diagnostic navigation
local function set_diagnostic_keymap(lhs, level)
    map("n", lhs, function()
        _G.set_diagnostic_level(level)
    end, { desc = "Set diagnostic level " .. tostring(level) })
end

_G.set_diagnostic_level(vim.diagnostic.severity.WARN)

set_diagnostic_keymap("<leader>d0", 0)
set_diagnostic_keymap("<leader>d1", vim.diagnostic.severity.ERROR)
set_diagnostic_keymap("<leader>d2", vim.diagnostic.severity.WARN)
set_diagnostic_keymap("<leader>d3", vim.diagnostic.severity.INFO)
set_diagnostic_keymap("<leader>d4", vim.diagnostic.severity.HINT)

-- Screenshots with silicon
map("v", "<leader>sc", function()
    require("silicon").capture_selection()
end, { desc = "Capture selection as image" })

-- Better indenting
map("v", "<", "<gv")
map("v", ">", ">gv")

-- Convert \n to actual newlines
map("n", "<leader>cn", function()
    vim.cmd([[%s/\\n/\r/g]])

    -- Then trigger the formatter
    -- Option 1: If using LSP-based formatting
    -- vim.lsp.buf.format({ async = false })

    -- Option 2: If using null-ls or conform.nvim
    require("conform").format()

    -- Option 3: If using a specific formatter command like prettier
    -- vim.cmd([[Prettier]])
    vim.notify("Converted \\n to newlines", vim.log.levels.INFO)
end, { desc = "Convert \\n to actual newlines" })
