local M = {}

local uv = vim.uv or vim.loop
local mode_file = vim.fn.expand("~/.config/ghostty/theme-mode")
local watcher
local timer
local group = vim.api.nvim_create_augroup("ghostty_theme_sync", { clear = true })
local mode_filename = vim.fn.fnamemodify(mode_file, ":t")

local function read_mode()
	local file = io.open(mode_file, "r")
	if not file then
		return nil
	end

	local mode = file:read("*l")
	file:close()

	if mode == "light" or mode == "dark" then
		return mode
	end
end

local function reload_rose_pine()
	if vim.g.colors_name == "rose-pine" then
		vim.cmd.colorscheme("rose-pine")
	end
end

function M.apply(mode, opts)
	opts = opts or {}
	mode = mode or read_mode()

	if mode ~= "light" and mode ~= "dark" then
		return
	end

	local changed = vim.o.background ~= mode
	if changed then
		vim.o.background = mode
	end

	if opts.reload ~= false and (changed or opts.force) then
		reload_rose_pine()
	end
end

local function schedule_apply()
	if not timer then
		timer = uv.new_timer()
	else
		timer:stop()
	end

	timer:start(
		50,
		0,
		vim.schedule_wrap(function()
			M.apply(nil, { force = true })
		end)
	)
end

function M.setup()
	M.apply(nil, { reload = false })

	local dir = vim.fn.fnamemodify(mode_file, ":h")
	if vim.fn.isdirectory(dir) == 0 then
		return
	end

	watcher = uv.new_fs_event()
	if not watcher then
		return
	end

	local ok = pcall(function()
		watcher:start(dir, {}, function(err, filename)
			if err then
				return
			end
			if filename and vim.fn.fnamemodify(filename, ":t") ~= mode_filename then
				return
			end
			schedule_apply()
		end)
	end)

	if not ok then
		watcher:close()
		watcher = nil
		return
	end

	vim.api.nvim_create_autocmd("VimLeavePre", {
		group = group,
		callback = function()
			if watcher and not watcher:is_closing() then
				watcher:stop()
				watcher:close()
			end

			if timer and not timer:is_closing() then
				timer:stop()
				timer:close()
			end
		end,
	})
end

return M
