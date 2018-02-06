# ISRUpdate
Small scrypt for update Cisco ISR G2 routers (C2900)

1. Connect to device
2. If more than two IOS images on flash  - delete oldest image
3. Upload new image
4. Delete all "boot system" commands, add command with new image
5. Reboot device at 1:00
