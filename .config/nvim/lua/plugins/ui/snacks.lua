return {
    "folke/snacks.nvim",
    event = "VimEnter",
    opts = {
        dashboard = {
            enabled = true,
            -- preset = {
            --     header = [[
            --  ███╗   ██╗███████╗ ██████╗ ██╗   ██╗██╗███╗   ███╗
            --  ████╗  ██║██╔════╝██╔═══██╗██║   ██║██║████╗ ████║
            --  ██╔██╗ ██║█████╗  ██║   ██║██║   ██║██║██╔████╔██║
            --  ██║╚██╗██║██╔══╝  ██║   ██║╚██╗ ██╔╝██║██║╚██╔╝██║
            --  ██║ ╚████║███████╗╚██████╔╝ ╚████╔╝ ██║██║ ╚═╝ ██║
            --  ╚═╝  ╚═══╝╚══════╝ ╚═════╝   ╚═══╝  ╚═╝╚═╝     ╚═╝]],
            -- },
            sections = {
                {
                    section = "terminal",
                    cmd = "chafa ~/.config/nvim/assets/wall.png --format symbols --symbols vhalf --size 60x17 --stretch; sleep .1",
                    height = 17,
                    padding = 1,
                },
                { section = "keys", gap = 1, padding = 1 },
                { section = "startup" },
            },
        },
        notifier = {
            enabled = true,
            timeout = 2000,
        },
    },
    dependencies = {
        "nvim-tree/nvim-web-devicons",
    },
    config = function(_, opts)
        require("snacks").setup(opts)
    end,
}
