# Setup raspberry 'krockis'

To set up the Raspberry Pi ("krockis"), you need some prerequisites (on Linux at least):

- ansible
- sshpass

Find its address/IP and run the following command.

```sh
ansible-playbook --extra-vars "username=pi core_addr=localhost:8001" -ki <address/IP of krockis>, ansible/setup-raspberry.yml
```

Replace `pi` with your custom username or `localhost:8001` with the address to where your core is running to dynamically
set these parameters. The same user and address will be applied to all components.

The following components will be run by default:
  - Media (fullscreen, without sound)
  - Inventory

## Limitations

  - At the moment it is not possible to choose which components
    to run without manually editing the ansible config file.
