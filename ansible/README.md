# Setup raspberry 'krockis'

To set up the Raspberry Pi ("krockis"), you need some prerequisites (on Linux at least):

- ansible
- sshpass

You should also have initialized the submodules in this repo:

```sh
git submodule update --init
```

## Manual setup

- Flash Raspberry Pi OS Desktop onto an SD card. Add a file `/boot/ssh`, and change `raspberry` to `krockis` in `/etc/hostname` and `/etc/hosts`.
- Put the card in the Raspberry Pi, turn it on, and SSH to it
- Change the password of the `pi` user
- Run `sudo raspi-config`, and disable screen blanking (under `2. Display Options`)

## Run playbook

Find its address/IP and run the following command.

```sh
ansible-playbook --extra-vars "username=pi core_addr=localhost:8001" -ki <address/IP of krockis>, ansible/setup-raspberry.yml
```

Replace `pi` with your custom username or `localhost:8001` with the address to where your core is running to dynamically
set these parameters. The same user and address will be applied to all components.

If this is the first time setting up Krockis, reboot it.

The following components will be run by default:

- Media (fullscreen, without sound)
- Inventory

## Limitations

- At the moment it is not possible to choose which components
  to run without manually editing the ansible config file.
