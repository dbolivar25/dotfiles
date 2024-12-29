local function augroup(name)
    return vim.api.nvim_create_augroup("lazyvim_" .. name, { clear = true })
end

-- Diagnostics configuration
local orig_diag_handler = vim.diagnostic.handlers.virtual_text
local ns = vim.api.nvim_create_namespace("custom_diagnostics")

local function filter_diagnostics(diagnostics, level)
    return vim.tbl_filter(function(d)
        return d.severity <= level
    end, diagnostics)
end

_G.set_diagnostic_level = function(level)
    vim.diagnostic.hide(nil, 0)
    vim.diagnostic.handlers.virtual_text = {
        show = function(_, bufnr, _, opts)
            local diagnostics = vim.diagnostic.get(bufnr)
            local filtered = filter_diagnostics(diagnostics, level)
            orig_diag_handler.show(ns, bufnr, filtered, opts)
        end,
        hide = function(_, bufnr)
            orig_diag_handler.hide(ns, bufnr)
        end,
    }

    local bufnr = vim.api.nvim_get_current_buf()
    local diagnostics = vim.diagnostic.get(bufnr)
    if #diagnostics > 0 then
        local filtered = filter_diagnostics(diagnostics, level)
        vim.diagnostic.show(ns, bufnr, filtered)
    end
end

-- Auto-formatting
vim.api.nvim_create_autocmd("FileType", {
    group = augroup("formatting"),
    pattern = { "ruby" },
    callback = function()
        vim.b.autoformat = false
    end,
})

vim.api.nvim_create_autocmd("LspProgress", {
    ---@param ev {data: {client_id: integer, params: lsp.ProgressParams}}
    callback = function(ev)
        local spinner = { "⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏" }
        vim.notify(vim.lsp.status(), "info", {
            id = "lsp_progress",
            title = "LSP Progress",
            opts = function(notif)
                notif.icon = ev.data.params.value.kind == "end" and " "
                    or spinner[math.floor(vim.uv.hrtime() / (1e6 * 80)) % #spinner + 1]
            end,
        })
    end,
})
