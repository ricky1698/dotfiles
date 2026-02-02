-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here

local keymap = vim.keymap

-- map esc to jk
keymap.set("i", "jk", "<Esc>", { desc = "jk to escape" })

-- keep cursor centered
keymap.set("n", "<C-d>", "<C-d>zz", { desc = "Scroll down and keep cursor centered" })
keymap.set("n", "<C-u>", "<C-u>zz", { desc = "Scroll up and keep cursor centered" })
keymap.set("n", "n", "nzzzv", { desc = "Move to next match and keep cursor centered" })
keymap.set("n", "N", "Nzzzv", { desc = "Move to previous match and keep cursor centered" })

-- tmux navigator
keymap.set("n", "<C-h>", "<Cmd>NvimTmuxNavigateLeft<CR>", { silent = true })
keymap.set("n", "<C-j>", "<Cmd>NvimTmuxNavigateDown<CR>", { silent = true })
keymap.set("n", "<C-k>", "<Cmd>NvimTmuxNavigateUp<CR>", { silent = true })
keymap.set("n", "<C-l>", "<Cmd>NvimTmuxNavigateRight<CR>", { silent = true })

-- ai
keymap.set("n", "<leader>aa", "<Cmd>CopilotChat<CR>", { silent = true })

-- Copy relative path to clipboard
vim.keymap.set("n", "<leader>r", function()
  local relative_path = vim.fn.expand("%:.")

  if relative_path then
    vim.fn.setreg("+", relative_path)
    vim.notify("Copied project-relative path:\n" .. relative_path, vim.log.levels.INFO)
  else
    vim.notify("Could not determine relative path.", vim.log.levels.WARN)
  end
end, { desc = "Copy path relative to project root" })
