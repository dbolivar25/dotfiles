return {
    {
        "stevearc/conform.nvim",
        opts = {
            formatters_by_ft = {
                -- Ansible
                ansible = { "ansible-lint" },

                -- Bash
                sh = { "shfmt", "beautysh" },

                -- C/C++
                c = { "clang-format" },
                cpp = { "clang-format" },

                -- Clojure
                clojure = { "cljfmt" },

                -- C#
                cs = { "csharpier" },

                -- Dockerfile
                dockerfile = { "hadolint" },

                -- Go
                go = {
                    "gofumpt",
                    "goimports",
                },

                -- Haskell
                haskell = { "fourmolu" },

                -- JSON
                json = { "prettier" },

                -- Lua
                lua = { "stylua" },

                -- Markdown
                markdown = {
                    "prettier",
                    "markdownlint",
                    "markdown-toc",
                },

                -- OCaml
                ocaml = { "ocamlformat" },

                -- PowerShell
                powershell = { "powershell-editor-services" },

                -- Protocol Buffers
                protobuf = { "protolint" },

                -- Python
                python = { "black", "ruff_format" },

                -- Ruby
                ruby = {
                    "rubocop",
                    "erb-formatter",
                },
                eruby = { "erb-formatter" },

                -- Rust
                rust = { "rustfmt" },

                -- SQL
                sql = {
                    "sqlfmt",
                    "sqlfluff",
                },

                -- TOML
                toml = { "taplo" },

                -- TypeScript/JavaScript
                typescript = { "prettier" },
                javascript = { "prettier" },
                javascriptreact = { "prettier" },
                typescriptreact = { "prettier" },

                -- Typst
                typst = { "typstyle" },

                -- YAML
                yaml = { "prettier" },

                -- Multiple/Other filetypes
                ["_"] = { "trim_whitespace", "trim_newlines" },
            },
            formatters = {
                prettier = {
                    prepend_args = { "--print-width", "80", "--prose-wrap", "always" },
                },
                shfmt = {
                    prepend_args = { "-i", "4", "-ci" },
                },
                black = {
                    prepend_args = { "--line-length", "100" },
                },
                sqlfluff = {
                    prepend_args = { "fix", "--force" },
                },
                stylua = {
                    prepend_args = { "--indent-type", "Spaces", "--indent-width", "4" },
                },
            },
        },
    },
}
