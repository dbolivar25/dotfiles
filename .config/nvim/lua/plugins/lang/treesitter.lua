return {
    {
        "nvim-treesitter/nvim-treesitter",
        opts = function(_, opts)
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
        end,
    },
}
