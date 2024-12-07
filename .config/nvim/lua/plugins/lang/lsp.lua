local language_id_of = {
    menhir = "ocaml.menhir",
    ocaml = "ocaml",
    ocamlinterface = "ocaml.interface",
    ocamllex = "ocaml.ocamllex",
    reason = "reason",
    dune = "dune",
}

return {
    {
        "neovim/nvim-lspconfig",
        event = { "BufReadPre", "BufNewFile" },
        dependencies = {
            { "folke/neoconf.nvim", cmd = "Neoconf", config = false },
            "mason.nvim",
            "williamboman/mason-lspconfig.nvim",
        },
        opts = {
            diagnostics = {
                underline = true,
                update_in_insert = false,
                virtual_text = {
                    spacing = 4,
                    source = "if_many",
                    prefix = "●",
                },
                severity_sort = true,
            },
            inlay_hints = {
                enabled = false,
            },
            capabilities = {},
            servers = {
                -- Ansible
                ansiblels = {},

                -- Bash
                bashls = {},

                -- Buffer
                bufls = {},

                -- C/C++
                clangd = {
                    capabilities = {
                        offsetEncoding = { "utf-16" },
                    },
                },

                -- Clojure
                clojure_lsp = {},

                -- C#
                csharp_ls = {
                    settings = {
                        csharp = {
                            solution = {
                                searchPaths = { "." },
                            },
                        },
                    },
                },

                -- Docker
                dockerls = {},
                docker_compose_language_service = {},

                -- Elixir
                elixirls = {},

                -- Go
                gopls = {
                    settings = {
                        gopls = {
                            gofumpt = true,
                            codelenses = {
                                gc_details = true,
                                generate = true,
                                regenerate_cgo = true,
                                test = true,
                                tidy = true,
                                upgrade_dependency = true,
                                vendor = true,
                            },
                            hints = {
                                assignVariableTypes = true,
                                compositeLiteralFields = true,
                                compositeLiteralTypes = true,
                                constantValues = true,
                                functionTypeParameters = true,
                                parameterNames = true,
                                rangeVariableTypes = true,
                            },
                        },
                    },
                },
                golangci_lint_ls = {},

                -- Haskell
                hls = {
                    settings = {
                        haskell = {
                            formattingProvider = "fourmolu",
                        },
                    },
                },

                -- Helm
                helm_ls = {},

                -- JSON
                jsonls = {
                    settings = {
                        json = {
                            schemas = require("schemastore").json.schemas(),
                            validate = { enable = true },
                        },
                    },
                },

                -- Lua
                lua_ls = {
                    settings = {
                        Lua = {
                            workspace = {
                                checkThirdParty = false,
                            },
                            completion = {
                                callSnippet = "Replace",
                            },
                            diagnostics = {
                                globals = { "vim" },
                            },
                        },
                    },
                },

                -- Markdown
                marksman = {},

                -- OCaml
                ocamllsp = {
                    get_language_id = function(_, ftype)
                        return language_id_of[ftype]
                    end,
                },

                -- PowerShell
                powershell_es = {},

                -- Prisma
                prismals = {},

                -- Python
                basedpyright = {
                    settings = {
                        python = {
                            analysis = {
                                autoImportCompletions = true,
                                typeCheckingMode = "strict",
                                autoSearchPaths = true,
                                useLibraryCodeForTypes = true,
                                diagnosticMode = "workspace",
                            },
                        },
                    },
                },

                -- Ruby
                ruby_lsp = {},

                -- Rust
                rust_analyzer = {
                    settings = {
                        ["rust-analyzer"] = {
                            cargo = {
                                buildScripts = {
                                    enable = true,
                                },
                            },
                            checkOnSave = true,
                            check = {
                                command = "clippy",
                                extraArgs = { "--all", "--", "-W", "clippy::all" },
                            },
                        },
                    },
                },

                -- SQL
                sqlls = {},

                -- TOML
                taplo = {},

                -- TypeScript/JavaScript
                tsserver = {
                    settings = {
                        typescript = {
                            inlayHints = {
                                includeInlayParameterNameHints = "all",
                                includeInlayParameterNameHintsWhenArgumentMatchesName = false,
                                includeInlayFunctionParameterTypeHints = true,
                                includeInlayVariableTypeHints = true,
                                includeInlayPropertyDeclarationTypeHints = true,
                                includeInlayFunctionLikeReturnTypeHints = true,
                                includeInlayEnumMemberValueHints = true,
                            },
                        },
                        javascript = {
                            inlayHints = {
                                includeInlayParameterNameHints = "all",
                                includeInlayParameterNameHintsWhenArgumentMatchesName = false,
                                includeInlayFunctionParameterTypeHints = true,
                                includeInlayVariableTypeHints = true,
                                includeInlayPropertyDeclarationTypeHints = true,
                                includeInlayFunctionLikeReturnTypeHints = true,
                                includeInlayEnumMemberValueHints = true,
                            },
                        },
                    },
                },

                -- YAML
                yamlls = {
                    settings = {
                        yaml = {
                            schemaStore = {
                                enable = true,
                                url = "https://www.schemastore.org/api/json/catalog.json",
                            },
                            schemas = {
                                kubernetes = "*.yaml",
                                ["http://json.schemastore.org/github-workflow"] = ".github/workflows/*",
                                ["http://json.schemastore.org/github-action"] = ".github/action.{yml,yaml}",
                                ["https://raw.githubusercontent.com/compose-spec/compose-spec/master/schema/compose-spec.json"] = "*docker-compose*.{yml,yaml}",
                                ["https://raw.githubusercontent.com/instrumenta/kubernetes-json-schema/master/v1.18.0-standalone-strict/all.json"] = "*.k8s.yaml",
                            },
                            validate = true,
                            format = {
                                enable = true,
                            },
                        },
                    },
                },
            },
            setup = {},
        },
    },
}
