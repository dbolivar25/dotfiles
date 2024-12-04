return {
	{
		"mfussenegger/nvim-lint",
		opts = {
			linters_by_ft = {
				-- Ansible
				-- ansible = { "ansible-lint" },

				-- Bash
				sh = { "shellcheck" },

				-- C/C++
				c = { "cpplint" },
				cpp = { "cpplint" },

				-- Clojure
				clojure = { "clj-kondo" },

				-- CMake
				cmake = { "cmakelint" },

				-- Dockerfile
				dockerfile = { "hadolint" },

				-- Go
				go = { "golangci-lint" },

				-- Haskell
				haskell = { "hlint" },

				-- Markdown
				markdown = {
					"markdownlint",
				},

				-- Protocol Buffers
				protobuf = { "protolint" },

				-- Python
				python = {
					"ruff",
					-- "pylint",
				},

				-- Ruby
				ruby = {
					"rubocop",
					-- "erb-lint",
				},
				eruby = { "erb-lint" },

				-- SQL
				sql = { "sqlfluff" },

				-- YAML
				yaml = { "yamllint" },
			},
			linters = {
				shellcheck = {
					args = {
						"--severity=warning",
						"--shell=bash",
						"--enable=all",
						"--format=json",
						"-",
					},
				},
				golangci_lint = {
					args = {
						"run",
						"--out-format=json",
						"--issues-exit-code=1",
					},
				},
			},
		},
	},
}
