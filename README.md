# homeassistant-milight-bluetooth

For underlying implementation details see https://github.com/souramoo/ReverseEngineeredMiLightBluetooth

## Usage

Get this into your custom_components folder:
```
cd custom_components
git clone https://github.com/souramoo/homeassistant-milight-bluetooth milight_bluetooth
```

Then include in your configuration.yaml
```
light:
  - platform: milight_bluetooth
    devices:
      bedroom:
        name: bedroom
        host: hci0
        mac: xx:xx:xx:xx:xx:xx
        id1: 10
        id2: 12
```
