import asyncio
import config
import uvicorn
import sys
import paho.mqtt.publish as publish
from siridb.connector import SiriDBClient
from typing import Optional
from fastapi import FastAPI, Request
from fastapi_versioning import VersionedFastAPI, version
from pprint import pprint
from pydantic import BaseModel
from ooop import OOOP

# models
class Login(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    token: str


# connect with Odoo
print('Connecting with Odoo...')
o = OOOP(
    user=config.Odoo.user,
    pwd=config.Odoo.pwd,
    dbname=config.Odoo.dbname,
    uri=config.Odoo.uri,
    port=config.Odoo.port,
    #debug=Odoo.debug
)

PRODUCTION = True

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

# asyncio loop
#loop = asyncio.get_event_loop()

# connect with siriDB
loop = asyncio.get_event_loop()

if PRODUCTION:
    siri = SiriDBClient(
        username=config.SIRIDB.username,
        password=config.SIRIDB.password,
        dbname=config.SIRIDB.dbname,
        hostlist=[(config.SIRIDB.host, config.SIRIDB.port)],  # Multiple connections are supported
        keepalive=True,
        loop=loop)
    #siri.connect()

async def _query_devices(user):
    # prepare DATA for user
    if user.role == 'superadmin':
        devices = o.Iot_devicesDevice.filter(domain_id='solarbox')
    elif user.role == 'user':
        devices = o.Iot_devicesDevice.filter(group_id__in=[i.id for i in user.group_ids])
    
    DATA = {}
    for device in devices:
        DATA[device.uuid] = {
            'uuid': device.uuid,
            'name': device.name,
            'state': 'offline',
            'group': device.group_id.name,
            'soc': 0,
            'switch_on': False,
            'switch_state': False,
            'switch_current': 0,
            'total_voltage': 0,
        }

    await siri.connect()
    res_uptime = await siri.query(f'select last() from /.*.uptime/ after now - 5m')
    res_soc = await siri.query(f'select last() from /.*.soc/ after now - 5m')
    res_switch_on = await siri.query(f'select last() from /.*.switch_on/ after now - 5m')
    res_switch_state = await siri.query(f'select last() from /.*.switch_state/ after now - 5m')
    res_switch_current = await siri.query(f'select last() from /.*.switch_current/ after now - 5m')
    res_total_voltage = await siri.query(f'select last() from /.*.total_voltage/ after now - 5m')



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

# TODO: check user / token
async def _query_device(device_id):
    await siri.connect()
    res_all = await siri.query(f'select last() from /{device_id}.*/ after now - 5m')
    # siri.close()

    device = o.Iot_devicesDevice.filter(uuid=device_id)[0]
    data = {
            'uuid': device.uuid,
            'name': device.name,
            'state': 'offline',
            'group': device.group_id.name,
            'soc': 0,
            'switch_on': False,
            'switch_state': False,
            'switch_current': 0,
            'total_voltage': 0,
        }

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

# endpoints
@app.post("/auth")
@version(1)
async def auth(login: Login):
    user = o.Iot_devicesUser.filter(email=login.email, password=login.password)
    if not user:
        res = {
        'authorized': False
    }
    else:
        res = {
            'authorized': True,
            'name': user[0].name,
            'token': user[0].uuid
        }
    return res

@app.post("/devices")
@version(1)
async def read_devices(token: Token):
    user = o.Iot_devicesUser.filter(uuid=token.token)
    if not user:
        return
    else:
        res = await _query_devices(user[0])
        return list(res.values())

# TODO: check user/token
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

# TODO: check user/token (observers can't launch actions)
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

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)