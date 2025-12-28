[![License](https://img.shields.io/github/license/edenhaus/ha-prosenic?style=for-the-badge)](LICENSE.md)

# Proscenic Home Assistant component
## Prior-art
* This is a fork based on [edenhaus work](https://github.com/edenhaus/ha-prosenic/tree/master)
* [FeikoJoosten fork](https://github.com/FeikoJoosten/ha-prosenic)
* [MrVidipy fork](https://github.com/MrVidipy/ha-proscenic)

This component is based on the underlying tinytuya library available [here](https://github.com/jasonacox/tinytuya).

## Installation

### HACS
If you have [HACS](https://hacs.xyz/) available in your Home Assistant then add this repository as a [custom respository](https://hacs.xyz/docs/faq/custom_repositories/)
 
### Manual
Copy the `custom_components/proscenic-850t-localtuya` directory into your `custom_components directory` so it looks like so:
```
└── ...
└── configuration.yaml
└── secrects.yaml
└── custom_components
    └── proscenic-850t-localtuya
        └── __init__.py
        └── const.py
        └── ...
```

**Note**: if the custom_components directory does not exist, you need to create it.

## Component setup

Once the component has been installed, you need to configure it in order to make it work.

First we need to find out the _device_id_, _ip address_ and _local key_ of your 850T.
The only way that I have found to do this is to use a rooted android phone or emulator, frida, termux and extract the key by tracing the official Android Proscenic App.
* https://community.home-assistant.io/t/retrieve-localkey-for-tuya-based-devices-using-bluestacks-and-frida/584550

### Configuration via editing configuration.yaml

1. Enable the component by editing the configuration.yaml file (within the config directory as well).
   Edit it by adding the following lines:

   ```yaml 
      vacuum: 
      - platform: "prosenic"
        name: "Vaccumie"
        host: "YOUR_HOST_IP"
        device_id: "YOUR_DEVICE_ID"
        local_key: "YOUR_LOCAL_KEY"
        remember_fan_speed: false #Optional, default false 
   ```
   **Note!** If you have already configured other vacuum robot, add your configuration there.

1. Reboot Home Assistant (check for any errors in the logs)
1. Congrats! You're all set! It should appear in Entities
