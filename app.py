#!/usr/bin/env python3

import asyncio
import time
import random
import json
import threading
import battery
#import paho.mqtt.client as mqtt
from datetime import datetime
from siridb.connector import SiriDBClient
#from asyncio_mqtt import Client, MqttError
from periodic import Periodic
from config import SIRIDB #, MQTT
from flask import Flask, escape, request, render_template, redirect, url_for

UUIDS = [
    '16ed78a6-4357-4742-a759-d605bb2ef75b',
    '3ca4664e-212e-4da2-ab7b-666e35e3ccd0',
    '455dbde7-18fe-4e49-a59a-acb0acdaaa04',
    '4db569d3-19b4-4e9f-9ef7-fef0d6832976',
    '5f884f63-0305-42b3-8c7c-9fddf08f490a',
    'b5c1920e-a900-4a9f-ad06-f476768f4528',
    'd3477f15-f827-4c97-9a39-f93c4e505b01',
    'd4db3a5c-669a-4b8f-afa4-df92298bffe5',
    'e06b98d8-205b-4fff-845f-f24d6a391856',
    'f42b6726-4914-4511-ad25-5192f330ed4e'
]


async def show(siri, id):
    # TODO: use pool
    data = {}
    await siri.connect()
    res = await siri.query(f'select last() from /{id}.*/ after now - 1h')
    siri.close()
    for k,v in res.items():
        if v:
            data[k[37:]] = v
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
    res  = loop.run_until_complete(show(siri,id))
    return render_template('device.html', id=id, data=dict(reversed(list(res.items()))))

@app.route('/devices')
def devices():
    return render_template('devices.html', ids=UUIDS)

@app.route('/')
def home():
    return redirect(url_for('devices'))
