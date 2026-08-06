local diagnostics = require("config.diagnostics")

local function ruby_root(markers)
	return function(bufnr, on_dir)
		local root = vim.fs.root(bufnr, markers)
		if root then
			on_dir(root)
		end
	end
end

local function terraform_root(bufnr, on_dir)
	local markers = { ".terraform", ".terraform.lock.hcl", "terraform.tf" }
	local root = vim.fs.root(bufnr, markers)
	local file = vim.api.nvim_buf_get_name(bufnr)
	on_dir(root or vim.fs.dirname(file))
end

return {
	{
		"neovim/nvim-lspconfig",
		opts = {
			diagnostics = {
				underline = true,
				update_in_insert = false,
				virtual_text = diagnostics.virtual_text(vim.diagnostic.severity.WARN),
				severity_sort = true,
			},
			inlay_hints = {
				enabled = false,
			},
			servers = {
				-- Servers without a matching LazyVim language extra.
				bashls = {},

				-- Intentional overrides for servers owned by language extras.
				biome = {
					-- Some projects keep container-built dependencies in the host checkout.
					cmd = { vim.fn.stdpath("data") .. "/mason/bin/biome", "lsp-proxy" },
				},
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
				ruby_lsp = {
					root_dir = ruby_root({ "Gemfile", "gems.rb" }),
				},
				rubocop = {
					root_dir = ruby_root({ "Gemfile", "gems.rb", ".rubocop.yml" }),
				},
				srb = { enabled = false },
				terraformls = {
					root_dir = terraform_root,
				},
				tflint = {
					root_dir = terraform_root,
				},
			},
		},
	},
}
