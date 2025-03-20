local function setup_baml_syntax()
    -- Define colors to match your theme style
    local colors = {
        keyword = "#43728C", -- Light blue for keywords
        literal = "#E4BC7E", -- Yellow for literals/strings
        default = "#FFFFFF", -- White for default text
        operator = "#8F8CA8", -- Dark gray for operators/punctuation
        type = "#A7CED7", -- Light green for types
        func = "#8F8CA8", -- Dark gray for functions
        comment = "#8F8CA8", -- Dark gray for comments
        docstring = "#A3A1BC", -- Lighter gray for docstrings
    }

    -- Clear any existing syntax rules
    vim.cmd([[syntax clear]])

    -- Basic keywords (grouped to reduce overhead)
    vim.cmd([[
        syntax keyword bamlKeyword function class enum test generator retry_policy client prompt template_string import impersonation select as use extends
    ]])

    -- Types (grouped)
    vim.cmd([[
        syntax keyword bamlType string number boolean array object image integer float int64 int32 float64 float32
    ]])

    -- Booleans
    vim.cmd([[
        syntax keyword bamlBoolean true false
    ]])

    -- Special annotations (simplified)
    vim.cmd([[
        syntax match bamlAnnotation "@[a-zA-Z_][a-zA-Z0-9_]*"
    ]])

    -- Operators and punctuation (combined patterns)
    vim.cmd([[
        syntax match bamlOperator "[+\-*/<>=!{}\[\](),;%|]"
        syntax match bamlOperator "->\\|==\\|!=\\|>=\\|<="
    ]])

    -- Numbers and strings (optimized)
    vim.cmd([[syntax match bamlNumber "\<\d\+\(\.\d\+\)\?\>"]])
    vim.cmd([[syntax region bamlString start=/"/ skip=/\\"/ end=/"/ contains=bamlStringEscape]])
    vim.cmd([[syntax match bamlStringEscape "\\." contained]])

    -- Multiline strings with template syntax
    vim.cmd([[
        syntax region bamlMultilineString start=/#"/ end=/"#/ contains=bamlMultilineVariable,bamlMultilineTag

        syntax region bamlMultilineVariable matchgroup=bamlMultilineVariableBraces start=/{{/ end=/}}/ contained
        syntax region bamlMultilineTag matchgroup=bamlMultilineTagBraces start=/{%/ end=/%}/ contained
    ]])

    -- Comments (combined into fewer rules)
    vim.cmd([[
        syntax match bamlComment "//[^/].*$"
        syntax match bamlDocstring "///.*$"
        syntax region bamlBlockComment start="/\*" end="\*/"
    ]])

    -- Template variables (combined into fewer patterns)
    vim.cmd([[
        syntax match bamlEnvVariable /\<env\.[a-zA-Z0-9_]*\>/
        syntax match bamlContextVariable /\<ctx\.[a-zA-Z0-9_]*\>/
    ]])

    -- Set up highlighting
    local function hi(group, opts)
        vim.api.nvim_set_hl(0, group, opts)
    end

    -- Apply highlighting (organized for clarity)
    -- Keywords and types
    hi("bamlKeyword", { fg = colors.keyword })
    hi("bamlType", { fg = colors.type })
    hi("bamlBoolean", { fg = colors.literal })

    -- Operators
    hi("bamlOperator", { fg = colors.operator })

    -- Strings
    hi("bamlString", { fg = colors.literal })
    hi("bamlMultilineString", { fg = colors.literal })
    hi("bamlStringEscape", { fg = colors.literal })

    -- Template syntax
    hi("bamlMultilineVariableBraces", { fg = colors.func })
    hi("bamlMultilineTagBraces", { fg = colors.func })

    -- Numbers
    hi("bamlNumber", { fg = colors.literal })

    -- Comments
    hi("bamlComment", { fg = colors.comment })
    hi("bamlDocstring", { fg = colors.docstring })
    hi("bamlBlockComment", { fg = colors.comment })

    -- Special syntax
    hi("bamlAnnotation", { fg = colors.func })
    hi("bamlDecorator", { fg = colors.func })
    hi("bamlEnvVariable", { fg = colors.literal })
    hi("bamlContextVariable", { fg = colors.literal })
end

return {
    setup = setup_baml_syntax,
}
