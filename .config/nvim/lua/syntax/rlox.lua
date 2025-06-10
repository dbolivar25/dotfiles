local M = {}

-- Define colors to match Rust implementation
local colors = {
    keyword = "#43728C", -- LightBlue
    literal = "#E4BC7E", -- Yellow
    default = "#FFFFFF", -- White
    operator = "#8F8CA8", -- DarkGray
}

-- Optimized vim syntax for fallback
local function setup_vim_syntax()
    -- Use buffer-local syntax rules to avoid clearing all syntax
    vim.cmd([[
        " Sync settings for large files - use fromstart for accuracy
        syntax sync fromstart
        
        " Keywords - use \< and \> for word boundaries
        syntax keyword rloxKeyword let rec fn if else while return and or struct nil
        syntax keyword rloxBoolean true false

        " Operators - simplified pattern
        syntax match rloxOperator "[+\-*/<>=!%]"
        syntax match rloxOperator "=="
        syntax match rloxOperator "!="
        syntax match rloxOperator ">="
        syntax match rloxOperator "<="
        syntax match rloxOperator "<>"
        syntax match rloxOperator "[{}[\](),;]"

        " Numbers - more efficient pattern
        syntax match rloxNumber "\<\d\+\(\.\d\+\)\?\>"
        
        " Strings - add keepend for better performance
        syntax region rloxString start=/"/ skip=/\\"/ end=/"/ contains=rloxStringEscape keepend
        syntax match rloxStringEscape "\\." contained

        " Comments - add keepend and oneline where appropriate
        syntax match rloxComment "//.*$" oneline
        syntax region rloxComment start="/\*" end="\*/" keepend

        " Set syntax as case-sensitive
        syntax case match
    ]])

    -- Set up highlighting
    local function hi(group, opts)
        vim.api.nvim_set_hl(0, group, opts)
    end

    hi("rloxKeyword", { fg = colors.keyword })
    hi("rloxBoolean", { fg = colors.literal })
    hi("rloxOperator", { fg = colors.operator })
    hi("rloxString", { fg = colors.literal })
    hi("rloxNumber", { fg = colors.literal })
    hi("rloxComment", { fg = colors.operator })
    hi("rloxStringEscape", { fg = colors.literal })
end

-- Main setup function
function M.setup()
    -- Use optimized vim syntax
    setup_vim_syntax()

    -- Set filetype-specific options for better performance
    vim.api.nvim_create_autocmd("FileType", {
        pattern = "rlox",
        callback = function()
            -- Limit syntax processing for very long lines
            vim.opt_local.synmaxcol = 500
            -- Enable faster scrolling
            vim.opt_local.lazyredraw = true
            -- Reduce update time for better responsiveness
            vim.opt_local.updatetime = 300
        end,
    })
end

-- Legacy compatibility
M.setup_rlox_syntax = M.setup

return M