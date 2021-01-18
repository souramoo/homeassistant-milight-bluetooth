# homeassistant-milight-bluetooth

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
      name: "Bedroom Light"
      host: "hci0"
      mac: "xx:xx:xx:xx:xx:xx"
      id1: 10
      id2: 12
```
