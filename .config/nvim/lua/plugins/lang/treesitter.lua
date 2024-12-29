return {
    {
        "nvim-treesitter/nvim-treesitter",
        opts = function(_, opts)
            -- Base configuration
            opts.ensure_installed = {
                "bash",
                "c",
                "cpp",
                "go",
                "lua",
                "python",
                "rust",
                "typescript",
                "vim",
                "haskell",
                "ocaml",
                "ruby",
                "json",
                "yaml",
                "toml",
                "query",
                "regex",
                "markdown",
                "markdown_inline",
            }
            opts.highlight = {
                enable = true,
                additional_vim_regex_highlighting = false,
            }
            opts.indent = { enable = true }
            opts.autotag = { enable = true }

            -- Register .rlox filetype
            vim.filetype.add({
                extension = {
                    rlox = "rlox",
                },
            })

            -- Set up autocmd for .rlox files
            vim.api.nvim_create_autocmd({ "BufRead", "BufNewFile" }, {
                pattern = "*.rlox",
                callback = function()
                    -- Set filetype
                    vim.opt_local.syntax = "rlox"

                    -- Load and setup syntax
                    local rlox_syntax = require("syntax.rlox")
                    rlox_syntax.setup()
                end,
            })

            return opts
        end,
    },
}
