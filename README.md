# Tmux Config

## Installation

After cloning, create a symlink at `~/.config/tmux/tmux.conf` to the configuration file in this repo via

```shell
mkdir -p ~/.config/tmux
ln -s ~/.config/tmux-config/tmux.conf ~/.config/tmux/tmux.conf
```

Also install tpm

```shell
git clone https://github.com/tmux-plugins/tpm ~/.config/tmux/plugins/tpm
```

Then resource configuration file

```shell
tmux source ~/.config/tmux/tmux.conf
```

And you're good to go!

