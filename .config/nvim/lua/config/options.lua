local opt = vim.opt

-- UI Options
opt.number = true
opt.relativenumber = true
opt.termguicolors = true
opt.showmode = false
opt.signcolumn = "yes"
opt.cursorline = true
-- opt.colorcolumn = "100"
opt.scrolloff = 8
opt.splitbelow = true
opt.splitright = true

-- Editing Options
opt.expandtab = true
opt.shiftwidth = 2
opt.tabstop = 2
opt.smartindent = true
opt.wrap = false
opt.timeoutlen = 300
opt.undofile = true
opt.undolevels = 10000

-- Search Options
opt.ignorecase = true
opt.smartcase = true
opt.inccommand = "split"

-- Performance Options
opt.hidden = true
opt.history = 100
-- opt.lazyredraw = true
opt.synmaxcol = 240
opt.updatetime = 250
