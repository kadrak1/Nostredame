# NAS Server Guidelines

## Storage Policy

- **Always use the SSD for installing services and storing files, never the SD card (memory card).**
  - All Docker containers, volumes, and configuration files must be placed on the SSD.
  - The SD card is used only for the OS boot partition; do not install services or store data on it.