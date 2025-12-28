[![License](https://img.shields.io/github/license/edenhaus/ha-prosenic?style=for-the-badge)](LICENSE.md)

# Proscenic Home Assistant component
## Prior-art
* This is a fork based on [edenhaus work](https://github.com/edenhaus/ha-prosenic/tree/master)
* [FeikoJoosten fork](https://github.com/FeikoJoosten/ha-prosenic)
* [MrVidipy fork](https://github.com/MrVidipy/ha-proscenic)

This component is based on the underlying tinytuya library available [here](https://github.com/jasonacox/tinytuya).

## Installation
TODO
## Component setup

Once the component has been installed, you need to configure it in order to make it work.

First we need to find out the _device_id_, _ip address_ and _local key_ of your proscenic vacuum cleaner. The only way that I have found to do this with the 850T is to use a rooted android phone or emulator, frida, termux and extract the key from official Proscenic App:
* https://community.home-assistant.io/t/retrieve-localkey-for-tuya-based-devices-using-bluestacks-and-frida/584550


### Configuration via editing configuration.yaml

1. Enable the component by editing the configuration.yaml file (within the config directory as well).
   Edit it by adding the following lines:

   ```yaml 
      vacuum: 
      - platform: "prosenic"
        host: "YOUR_HOST_IP"
        device_id: "YOUR_DEVICE_ID"
        local_key: "YOUR_LOCAL_KEY"
        remember_fan_speed: false #Optional, default false 
   ```
   **Note!** If you have already configured other vacuum robot, add your configuration there.

1. Reboot hassio (check for any errors in the logs)
1. Congrats! You're all set! It should appear in Entities

