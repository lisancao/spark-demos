-- Film-only Neovim config: `nvim -u "$FILM_KIT/nvim-film.lua" <file>`.
-- Reuses the plugins already installed for ~/.config/nvim (never installs,
-- never touches its lazy-lock.json) and sets up only what reads on camera:
-- a colour scheme, nvim-tree, lualine, treesitter highlighting. No LSP, so no
-- diagnostics from an unrelated venv end up in the shot.
local plugroot = vim.fn.expand("~/.local/share/nvim/lazy")
vim.opt.rtp:prepend(plugroot .. "/lazy.nvim")

vim.g.mapleader = " "
vim.g.loaded_netrw = 1
vim.g.loaded_netrwPlugin = 1

require("lazy").setup({
  { "lunarvim/synthwave84.nvim" },
  { "nvim-tree/nvim-web-devicons" },
  { "nvim-tree/nvim-tree.lua" },
  { "nvim-lualine/lualine.nvim" },
  { "nvim-treesitter/nvim-treesitter" },
}, {
  root = plugroot,
  lockfile = vim.fn.stdpath("state") .. "/nvim-film-lock.json",
  install = { missing = false },
  checker = { enabled = false },
  change_detection = { enabled = false },
  rocks = { enabled = false },
})

vim.opt.termguicolors = true
vim.opt.number = true
vim.opt.relativenumber = false -- absolute numbers read better on camera
vim.opt.cursorline = true
vim.opt.swapfile = false
vim.opt.showmode = false -- lualine shows the mode
vim.opt.laststatus = 3
vim.opt.signcolumn = "no"
vim.opt.scrolloff = 6
-- Wrap instead of cutting off the ends of long lines: after :Run the code has the
-- narrower share of the frame.
vim.opt.wrap = true
vim.opt.linebreak = true
vim.opt.breakindent = true

-- FILM_THEME=spark: a warm built-in scheme on the Spark terminal theme's background.
if vim.env.FILM_THEME == "spark" then
  vim.cmd("colorscheme retrobox")
  for _, g in ipairs({ "Normal", "NormalNC", "NvimTreeNormal", "NvimTreeNormalNC", "SignColumn", "EndOfBuffer" }) do
    vim.api.nvim_set_hl(0, g, { fg = "#ece6df", bg = "#141215" })
  end
  vim.api.nvim_set_hl(0, "CursorLine", { bg = "#26232a" })
  vim.api.nvim_set_hl(0, "CursorLineNr", { fg = "#E25A1C", bold = true })
else
  vim.cmd("colorscheme synthwave84")
end

require("nvim-tree").setup({
  view = { width = 26 },
  renderer = { group_empty = true, root_folder_label = ":t" },
  filters = { dotfiles = true, custom = { "^\\.venv", "^__pycache__$", "^\\.git$", "^data$" } },
  git = { enable = false },
})
require("lualine").setup({
  options = { theme = "auto", globalstatus = true, section_separators = "", component_separators = "" },
  sections = { lualine_b = {}, lualine_x = { "filetype" }, lualine_y = {}, lualine_z = { "location" } },
})

-- nvim-treesitter's main branch: highlighting is started per buffer.
vim.api.nvim_create_autocmd("FileType", {
  callback = function(ev) pcall(vim.treesitter.start, ev.buf) end,
})

-- On a phone-width frame the tree would take half the code's width, so the vertical
-- format keeps `<leader>e` but leaves the tree closed.
if vim.env.FILM_FORMAT == "vertical" then
  vim.keymap.set("n", "<leader>e", "<Nop>")
else
  vim.keymap.set("n", "<leader>e", ":NvimTreeToggle<CR>", { silent = true })
end

-- :Run runs the current file in a terminal beside the code (below it in the vertical
-- format), so the query stays on screen while its output arrives. Focus goes back to
-- the code; the terminal keeps following the output.
vim.api.nvim_create_user_command("Run", function()
  local file = vim.fn.expand("%")
  if vim.env.FILM_FORMAT == "vertical" then
    vim.cmd("botright new | resize 36")
  else
    vim.cmd("botright vnew | vertical resize 58")
  end
  -- Before the terminal starts, so the program gets the window's full width.
  vim.opt_local.number = false
  vim.opt_local.cursorline = false
  vim.cmd("terminal python " .. vim.fn.shellescape(file))
  vim.cmd("normal! G")
  vim.cmd("wincmd p")
end, {})
