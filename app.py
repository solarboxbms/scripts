#!/usr/bin/env python3

import asyncio
import time
import random
import json
import threading
import battery
import humanize
#import paho.mqtt.client as mqtt
from datetime import datetime
from siridb.connector import SiriDBClient
#from asyncio_mqtt import Client, MqttError
#from periodic import Periodic
from config import Odoo, SIRIDB, GROUPS, DEVICES, UUIDS #, MQTT
from flask import Flask, escape, request, render_template, redirect, url_for
from ooop import OOOP

# connect with Odoo
print('Connecting with Odoo...')
o = OOOP(
    user=Odoo.user,
    pwd=Odoo.pwd,
    dbname=Odoo.dbname,
    uri=Odoo.uri,
    port=Odoo.port,
    #debug=Odoo.debug
)

async def show_device(siri, id):
    # TODO: use pool
    data = {}
    await siri.connect()
    res = await siri.query(f'select last() from /{id}.*/ after now - 1h')
    siri.close()
    print(res)
    if f'{id}.voltages.1' in res:
        delta = datetime.now() - datetime.fromtimestamp(res[f'{id}.voltages.1'][0][0])
        moment = humanize.naturaldelta(delta)
    else:
        moment = 'no data yet...'
    for k,v in res.items():
        if v:
            data[k[37:]] = v
    return moment, data

async def show_devices(siri):
    # get uptime info for devices
    await siri.connect()
    # uptime
    res_uptime = await siri.query(f'select last() from /.*.uptime/ after now - 1h')
    # res_voltage = await siri.query(f'select last() from /.*.total_voltage/ after now - 1h')
    siri.close()

    # read devices from odoo
    devices = o.Iot_devicesDevice.filter(fields=['name', 'uuid', 'group_id'], as_list=True)
    groups = dict([(i.uuid, i.group_id[1]) for i in devices])
    # .split('/')[0].strip()

    data = {}
    for device in devices:
        group = device.group_id[1]
        # add group it isn't exists
        if not group in data:
            data[group] = {}
        # add device to group
        data[group][device.uuid] = {
            'name': device.name,
            #'since': moment
        }
    
    # add uptime
    for k,v in res_uptime.items():
        if v:
            delta = datetime.now() - datetime.fromtimestamp(v[0][0])
            moment = humanize.naturaldelta(delta)
            key = k.split('.')[0]
            group = groups[key]
            data[group][key]['since'] = moment
    """
    for k,v in res_uptime.items():
        if v:
            delta = datetime.now() - datetime.fromtimestamp(v[0][0])
            moment = humanize.naturaldelta(delta)
            key = k.split('.')[0]
            group = UUIDS[key]
            data[group][key] = {
                'name': DEVICES[group][key]['name'],
                'since': moment
            }
    """
    return data


loop = asyncio.get_event_loop()
# loop.run_until_complete(show(siri))
siri = SiriDBClient(
        username=SIRIDB.username,
        password=SIRIDB.password,
        dbname=SIRIDB.dbname,
        hostlist=[(SIRIDB.host, SIRIDB.port)],  # Multiple connections are supported
        keepalive=True,
        loop=loop)

app = Flask(__name__)


@app.route('/device/<id>')
def device(id=None):
    #tasks = [asyncio.async(show(siri,id))]
    #tasks = [getattr(asyncio, 'async')(show(siri,id))]
    #loop = asyncio.get_event_loop()
    moment, data  = loop.run_until_complete(show_device(siri,id))
    return render_template('device.html', id=id, moment=moment, data=dict(reversed(list(data.items()))))

@app.route('/devices')
def devices():
    data  = loop.run_until_complete(show_devices(siri))
    return render_template('devices.html', data=data)

@app.route('/')
def home():
    return redirect(url_for('devices'))
