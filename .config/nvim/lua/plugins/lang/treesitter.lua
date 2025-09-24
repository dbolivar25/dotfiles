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

            -- Register custom filetype
            vim.filetype.add({
                extension = {
                    rlox = "rlox",
                    baml = "baml",
                },
            })

            -- Register BAML parser with tree-sitter
            local parser_config = require("nvim-treesitter.parsers").get_parser_configs()
            parser_config.baml = {
                install_info = {
                    url = "~/Projects/treesitter/tree-sitter-baml",
                    files = { "src/parser.c", "src/scanner.c" },
                    generate_requires_npm = false,
                    requires_generate_from_grammar = false,
                },
                filetype = "baml",
            }

            -- Set up autocmd for .rlox files
            vim.api.nvim_create_autocmd({ "BufRead", "BufNewFile" }, {
                pattern = "*.rlox",
                callback = function()
                    -- Set filetype
                    vim.opt_local.filetype = "rlox"

                    -- Load and setup syntax
                    local rlox_syntax = require("syntax.rlox")
                    rlox_syntax.setup()
                end,
            })

            -- Set up autocmd for .baml files (template highlighting)
            vim.api.nvim_create_autocmd({ "BufRead", "BufNewFile" }, {
                pattern = "*.baml",
                callback = function()
                    -- Set filetype
                    vim.opt_local.filetype = "baml"

                    -- Load and setup syntax
                    local baml_syntax = require("syntax.baml")
                    baml_syntax.setup()
                end,
            })

            return opts
        end,
    },
}
