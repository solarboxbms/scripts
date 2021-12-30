import asyncio
import config
import paho.mqtt.publish as publish
from siridb.connector import SiriDBClient
from typing import Optional
from fastapi import FastAPI
from fastapi_versioning import VersionedFastAPI, version
from pprint import pprint




# TODO: add i18n/helpers - detail info of variables
# TODO: device structure with type
DEVICE_KEYS = [
    'micro_temperature',
    'switch_temperature',
    'batt_temperature_2', # Ambient
    'batt_temperature_1', # Battery
    'soc',
    'switch_current',
    'total_voltage',
]

DEVICE_KEYS_BOOLEAN = [
    'switch_on',
    'switch_state',
]

# set groups by uuid
DATA = {}
for k1, v1 in config.DEVICES.items():
    for k2, v2 in v1.items():
        DATA[k2] = {
            'uuid': k2,
            'name': v2['name'],
            'state': 'offline',
            'group': v2['group'],
            'soc': 0,
            'switch_on': False,
            'switch_state': False,
            'switch_current': 0,
            'total_voltage': 0,
        }

# asyncio loop
loop = asyncio.get_event_loop()

# connect with siriDB
loop = asyncio.get_event_loop()
siri = SiriDBClient(
    username=config.SIRIDB.username,
    password=config.SIRIDB.password,
    dbname=config.SIRIDB.dbname,
    hostlist=[(config.SIRIDB.host, config.SIRIDB.port)],  # Multiple connections are supported
    keepalive=True,
    loop=loop)
siri.connect()

async def _query_devices():
    await siri.connect()
    res_uptime = await siri.query(f'select last() from /.*.uptime/ after now - 5m')
    res_soc = await siri.query(f'select last() from /.*.soc/ after now - 5m')
    res_switch_on = await siri.query(f'select last() from /.*.switch_on/ after now - 5m')
    res_switch_state = await siri.query(f'select last() from /.*.switch_state/ after now - 5m')
    res_switch_current = await siri.query(f'select last() from /.*.switch_current/ after now - 5m')
    res_total_voltage = await siri.query(f'select last() from /.*.total_voltage/ after now - 5m')

    # pprint(DATA)

    # set offline
    for device_id in DATA.keys():
        DATA[device_id]['state'] = 'offline'

    for k, v in res_soc.items():
        if v and '.' in k:
            device_id = k.split('.')[0]
            if device_id in DATA:
                DATA[device_id]['soc'] = v and v[0][1] or 0
                DATA[device_id]['state'] = 'online'
            elif v:
                print(f'ERROR! UUID {device_id} not in DATA', v)

    for k, v in res_switch_on.items():
        if v and '.' in k:
            device_id = k.split('.')[0]
            if device_id in DATA:
                DATA[device_id]['switch_on'] = v[0][1] and True or False

    for k, v in res_switch_state.items():
        if v and '.' in k:
            device_id = k.split('.')[0]
            if device_id in DATA:
                DATA[device_id]['switch_state'] = v[0][1] and True or False

    for k, v in res_switch_current.items():
        if v and '.' in k:
            device_id = k.split('.')[0]
            if device_id in DATA:
                DATA[device_id]['switch_current'] = v and v[0][1] or 0

    for k, v in res_total_voltage.items():
        if v and '.' in k:
            device_id = k.split('.')[0]
            if device_id in DATA:
                DATA[device_id]['total_voltage'] = v and v[0][1] or 0

    return DATA

async def _query_device(device_id):
    await siri.connect()
    res_all = await siri.query(f'select last() from /{device_id}.*/ after now - 5m')
    # siri.close()

    data = DATA[device_id]
    cell_voltages = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    for k, v in res_all.items():
        if v:
            # save cell voltages (partialy)
            if 'voltages' in k:
                cell = int(k.split('.')[2]) - 1
                cell_voltages[cell] = v[0][1]
            elif '.' in k:
                key = '.'.join(k.split('.')[1:])
                if key in DEVICE_KEYS:
                    data[key] = v and v[0][1] or 0
                if key in DEVICE_KEYS_BOOLEAN:
                    data[key] = v[0][1] and True or False
    # include cell voltages
    data['cells'] = cell_voltages

    return data

app = FastAPI()

@app.get("/devices")
@version(1)
async def read_devices():
    data = await _query_devices()
    return list(data.values())

@app.get("/device/{device_id}")
@version(1)
async def read_device(device_id: str): #, q: Optional[str] = None):
    # mqtt data
    data = await _query_device(device_id)
    topic = f'solarbox/{device_id}/action'
    payload = 'battery'
    # publish
    publish.single(
        topic, payload=payload, hostname="mqtt.solarbox.xyz",
        port=1883, client_id="API", keepalive=60
    )
    return data

@app.get("/device/{device_id}/switch/{new_switch_state}")
@version(1)
async def change_switch(device_id: str, new_switch_state: str): #, q: Optional[str] = None):
    # mqtt data
    topic = f'solarbox/{device_id}/action'
    if new_switch_state == 'true':
        payload = 'on'
    else:
        payload = 'off'
    print(topic, payload)
    # publish switch action
    publish.single(
        topic, payload=payload, hostname="mqtt.solarbox.xyz",
        port=1883, client_id="API", keepalive=60
    )
    await asyncio.sleep(2)
    # get data again
    payload = 'battery'
    publish.single(
        topic, payload=payload, hostname="mqtt.solarbox.xyz",
        port=1883, client_id="API", keepalive=60
    )
        #will=None,
        #auth={username:"user", password:"pass"}, tls=None,
        #protocol=mqtt.MQTTv311, transport="tcp")
    return '{"status": "done"}'


# https://stackoverflow.com/questions/66390509/how-to-set-fast-api-version-to-allow-http-can-specify-version-in-accept-header
app = VersionedFastAPI(app,
    version_format='{major}',
    prefix_format='/v{major}')
