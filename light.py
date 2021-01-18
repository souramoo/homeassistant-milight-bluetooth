import logging
import urllib.request
import voluptuous as vol
import colorsys
import time
import threading
import pickle
import logging
import subprocess
import os.path

from queue import Queue

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_HS_COLOR, ATTR_COLOR_TEMP, LightEntity, PLATFORM_SCHEMA,  SUPPORT_BRIGHTNESS, SUPPORT_COLOR, SUPPORT_COLOR_TEMP
import homeassistant.helpers.config_validation as cv
import homeassistant.util.color as color_util

_LOGGER = logging.getLogger(__name__)
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({})


from homeassistant.const import CONF_MAC, CONF_CLIENT_ID, CONF_DEVICE_ID, CONF_HOST, CONF_ENTITY_ID
from homeassistant.components.light import PLATFORM_SCHEMA

LIGHT_SCHEMA = vol.All(
    cv.deprecated(CONF_ENTITY_ID),
    vol.Schema(
        {
            vol.Optional("name"): cv.string,
            vol.Optional("host"): cv.string,
            vol.Optional("mac"): cv.string,
            vol.Optional("id1"): cv.port,
            vol.Optional("id2"): cv.port
        }
    ),
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Required("devices"): cv.schema_with_slug_keys(LIGHT_SCHEMA)}
)


subprocess.call(['/sbin/apk', 'add', 'bluez-deprecated'])
import os
cwd = os.getcwd()
_LOGGER.info(cwd)

def setup_platform(hass, config, add_devices, discovery_info=None):
    devs = []
    for device, device_config in config["devices"].items():
        devs.append(MiLightSm(device_config["id1"], device_config["id2"], device_config["mac"], device_config["host"], device_config["name"]))
    add_devices(devs)

class GattQueue(threading.Thread):
    def __init__(self, mac, dev, args=(), kwargs=None):
        threading.Thread.__init__(self, args=(), kwargs=None)
        self.queue = Queue()
        self.dev = dev
        self.mac = mac
        self.daemon = True

    def run(self):
#        _LOGGER.error("Started thread...")
        while True:
            val = self.queue.get()
#            _LOGGER.error(val)
            ret = subprocess.call(['/usr/bin/gatttool', '-i', self.dev, '-b', self.mac, '--char-write-req', '-a', '0x0012', '-n', val])
#            _LOGGER.error(" ".join(['/usr/bin/gatttool', '-i', self.dev, '-b', self.mac, '--char-write-req', '-a', '0x0012', '-n', val]))

            if ret is not 0:
#                _LOGGER.error("Failed, trying again once.")
                ret = subprocess.call(['/usr/bin/gatttool', '-i', self.dev, '-b', self.mac, '--char-write-req', '-a', '0x0012', '-n', val])
                if ret is not 0:
#                    _LOGGER.error("Failed, trying again twice.")
                    subprocess.call(['/usr/bin/gatttool', '-i', self.dev, '-b', self.mac, '--char-write-req', '-a', '0x0012', '-n', val])

class MiLightSm(LightEntity):
    def __init__(self, id1, id2, mac, interface, name):
        self._name = name

        self.id1 = id1
        self.id2 = id2
        qu = GattQueue(mac, interface)
        self.q = qu.queue
        qu.start()
 #       _LOGGER.error("start1")
        if os.path.isfile("./persist/"+str(self.id1)):
            f = open("./persist/"+str(self.id1), "rb")
            self.setParameters(pickle.load(f))
            f.close()
            self.apply()
        else:
            self._state = False
            self._brightness = 100
            self.mode = 1 # 1=temp, 0=color
            self._color = 0
            self._temperature = 100
            self.setStatus(self._state)
            self.apply()

    @property
    def name(self):
        return self._name

    @property
    def brightness(self):
        return int(self._brightness/100*255)

    @property
    def color_temp(self):
        return self._temperature

    @property
    def color_hs(self):
        colors = colorsys.hsv_to_rgb(self._color,1,1)
        return color_util.color_RGB_to_hs(int(colors[0]*256), int(colors[1]*256), int(colors[2]*256))

    @property
    def hs_color(self):
        colors = colorsys.hsv_to_rgb(self._color,1,1)
        return color_util.color_RGB_to_hs(int(colors[0]*256), int(colors[1]*256), int(colors[2]*256))

    @property
    def is_on(self):
        return self._state

    @property
    def supported_features(self):
        return SUPPORT_BRIGHTNESS | SUPPORT_COLOR | SUPPORT_COLOR_TEMP

    def turn_on(self, **kwargs):
        self._state = True
        if ATTR_COLOR_TEMP in kwargs:
            temp = kwargs[ATTR_COLOR_TEMP]
            self.setParameterInternal("temp", int(temp))
            self.setParameterInternal("mode", 1)
        if ATTR_HS_COLOR in kwargs:
            rgb = color_util.color_hs_to_RGB(*kwargs[ATTR_HS_COLOR])
            hsv = colorsys.rgb_to_hsv(rgb[0], rgb[1], rgb[2])
            # if its white, make it white
            #_LOGGER.error(hsv)
            if hsv[2] == 1 or (hsv[2] == 255 and hsv[0] == 0.09959349593495935):
                self.setParameterInternal("temp", self._temperature)
                self.setParameterInternal("mode", 1)
            elif hsv[2] == 250: # cool white
                self.setParameterInternal("temp", 100)
                self.setParameterInternal("mode", 1)
            elif hsv[2] == 230: # gold
                self.setParameterInternal("temp", 255)
                self.setParameterInternal("mode", 1)
            else:
                # otherwise, set colour
                self.setParameterInternal("color", int(hsv[0]*255))
                self.setParameterInternal("mode", 0)
        if ATTR_BRIGHTNESS in kwargs:
            self.setParameterInternal("brightness", int(int(kwargs[ATTR_BRIGHTNESS])/255*100))
        self.setParameterInternal("status", True)
        self.apply()

    def turn_off(self, **kwargs):
        self._state = False
        self.setParameterInternal("status", False)

    def update(self):
        pass

    def setStatus(self, state):
        self._state = state
        if not state:
            self.q.put(self.createPacket([85, 161, self.id1, self.id2, 2, 2, 0, 0, 0, 0, 0]))
        else:
            self.q.put(self.createPacket([32, 161, self.id1, self.id2, 2, 1, 0, 0, 0, 0, 0]))

    def setParameterInternal(self, param, value):
        if param == "status":
            self.setStatus(int(value))
        elif param == "mode":
            self.mode = int(value)
        elif param == "color":
            self._color = int(value)
        elif param == "temp":
            self._temperature = int(value)
        elif param == "brightness":
            self._brightness = int(value)

    def apply(self):
        if self.mode == 0:
            self.q.put(self.createPacket([85, 161, self.id1, self.id2 , 2, 4, self._color, 100, 0, 0, 0]))
            self.q.put(self.createPacket([85, 161, self.id1, self.id2, 2, 5, self._color, self._brightness, 0, 0, 0]))
        elif self.mode == 1:
            self.q.put(self.createPacket([20, 161, self.id1, self.id2, 4, 4, self._temperature, 255, 0, 0, 0]))
            self.q.put(self.createPacket([20, 161, self.id1, self.id2 , 4, 5, self._temperature, self._brightness, 0, 0, 0]))
        f = open( "./persist/"+str(self.id1), "wb" )
        pickle.dump(self.getParameters(), f)
        f.close()

    def createPacket(self, data):
        input = data

        k = input[0]
        # checksum
        j = 0
        i = 0

        while i <= 10:
            j += input[i] & 0xff
            i += 1
        checksum = ((( (k ^ j) & 0xff) + 131) & 0xff)

        xored = [(s&0xff)^k for s in input]

        offs = [0, 16, 24, 1, 129, 55, 169, 87, 35, 70, 23, 0]

        adds = [x+y&0xff for(x,y) in zip(xored, offs)]

        adds[0] = k
        adds.append(checksum)

        hexs = [hex(x) for x in adds]
        hexs = [x[2:] for x in hexs]
        hexs = [x.zfill(2) for x in hexs]

        return ''.join(hexs)

        ##### DEPRECATED ############
    def setParameter(self, param, value):
        if param == "status":
            self.setStatus(bool(value))
        elif param == "mode":
            self.mode = int(value)
        elif param == "color":
            self._color = int(value)
            self.mode = 0
        elif param == "temp":
            self._temperature = int(value)
            self.mode = 1
        elif param == "brightness":
            self._brightness = int(value)
        self.apply()
        time.sleep(0.2)

    def setParameters(self, list):
        internal = False
        if list[0][0] == "status":
            internal = True
        for a in list:
            if internal == True:
                self.setParameterInternal(a[0], a[1])
            else:
                self.setParameter(a[0], a[1])
        self.apply()


    def getParameters(self):
        return [ ["status", self._state],
                 ["mode", self.mode],
                 ["color", self._color],
                 ["temp", self._temperature],
                 ["brightness", self._brightness] ]

