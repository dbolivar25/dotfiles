return {
	{
		"mfussenegger/nvim-lint",
		opts = {
			linters_by_ft = {
				c = { "cpplint" },
				cmake = { "cmakelint" },
				cpp = { "cpplint" },
				dockerfile = { "hadolint" },
				protobuf = { "protolint" },
				sh = { "shellcheck" },
				terraform = {},
				tf = {},
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
			},
		},
	},
}
