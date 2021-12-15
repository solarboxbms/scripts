import asyncio
import config
from siridb.connector import SiriDBClient
from typing import Optional
from fastapi import FastAPI
from fastapi_versioning import VersionedFastAPI, version
from pprint import pprint

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
            'switch_on': 0,
            'switch_state': 0,
            'switch_current': 0,
            'total_voltage': 0
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

async def query():
    await siri.connect()
    res_uptime = await siri.query(f'select last() from /.*.uptime/ after now - 5m')
    res_soc = await siri.query(f'select last() from /.*.soc/ after now - 5m')
    res_switch_on = await siri.query(f'select last() from /.*.switch_on/ after now - 5m')
    res_switch_state = await siri.query(f'select last() from /.*.switch_state/ after now - 5m')
    res_switch_current = await siri.query(f'select last() from /.*.switch_current/ after now - 5m')
    res_total_voltage = await siri.query(f'select last() from /.*.total_voltage/ after now - 5m')

    siri.close()
    # set offline
    pprint(DATA)
    for oid in DATA.keys():
        DATA[oid]['state'] = 'offline'

    for k, v in res_soc.items():
        if '.' in k:
            oid = k.split('.')[0]
            if oid in DATA:
                DATA[oid]['soc'] = v and v[0][1] or 0
                DATA[oid]['state'] = 'online'
            elif v:
                print(f'ERROR! UUID {oid} not in DATA', v)

    for k, v in res_switch_on.items():
        if '.' in k:
            oid = k.split('.')[0]
            if oid in DATA:
                DATA[oid]['switch_on'] = v and v[0][1] or 0

    for k, v in res_switch_state.items():
        if '.' in k:
            oid = k.split('.')[0]
            if oid in DATA:
                DATA[oid]['switch_state'] = v and v[0][1] or 0

    for k, v in res_switch_current.items():
        if '.' in k:
            oid = k.split('.')[0]
            if oid in DATA:
                DATA[oid]['switch_current'] = v and v[0][1] or 0

    for k, v in res_total_voltage.items():
        if '.' in k:
            oid = k.split('.')[0]
            if oid in DATA:
                DATA[oid]['total_voltage'] = v and v[0][1] or 0

app = FastAPI()

@app.get("/devices")
@version(1)
async def read_root():
    res = await query()
    return list(DATA.values())

@app.get("/items/{item_id}")
@version(1)
def read_item(item_id: int, q: Optional[str] = None):
    return {"item_id": item_id, "q": q}

# https://stackoverflow.com/questions/66390509/how-to-set-fast-api-version-to-allow-http-can-specify-version-in-accept-header
app = VersionedFastAPI(app,
    version_format='{major}',
    prefix_format='/v{major}')
