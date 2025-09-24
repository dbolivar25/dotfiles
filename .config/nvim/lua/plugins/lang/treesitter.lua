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
                "prisma",
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
            -- local parsers = require("nvim-treesitter.parsers")
            -- parsers.baml = {
            --     install_info = {
            --         path = vim.fn.expand("~/Projects/treesitter/tree-sitter-baml"),
            --         files = { "src/parser.c", "src/scanner.c" },
            --         generate = false,
            --         generate_from_json = false,
            --         queries = vim.fn.expand("~/Projects/treesitter/tree-sitter-baml/queries/baml"),
            --     },
            --     filetype = "baml",
            --     tier = 1,
            -- }

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
                callback = function(args)
                    -- Set filetype
                    vim.opt_local.filetype = "baml"

                    vim.treesitter.start(args.buf, "baml")

                    -- Load and setup syntax
                    local baml_syntax = require("syntax.baml")
                    baml_syntax.setup()
                end,
            })

            return opts
        end,
    },
}
