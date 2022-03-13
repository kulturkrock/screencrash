# Setup raspberry 'krockis'

To set up the Raspberry Pi ("krockis"), you need some prerequisites (on Linux at least):

- ansible
- sshpass

Find its address/IP and run the following command.

```sh
ansible-playbook -ki <address/IP of krockis>, ansible/setup-raspberry.yml
```

## Limitations

- Currently only the media component
- Fullscreen does not work properly, go into the media component source and change
  the window size manually to the projector resolution
