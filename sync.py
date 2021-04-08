#!/usr/bin/env python3

import asyncio
import time
import random
import json
import battery
import paho.mqtt.client as mqtt
from siridb.connector import SiriDBClient
from asyncio_mqtt import Client, MqttError
from periodic import Periodic
from config import SIRIDB, MQTT

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

siri = SiriDBClient(
    username=SIRIDB.username,
    password=SIRIDB.password,
    dbname=SIRIDB.dbname,
    hostlist=[(SIRIDB.host, SIRIDB.port)],  # Multiple connections are supported
    keepalive=True)


async def update(siri):
    # Start connecting to SiriDB.
    # .connect() returns a list of all connections referring to the supplied
    # hostlist. The list can contain exceptions in case a connection could not
    # be made.

    p = Periodic(MQTT.period, action_battery)
    await p.start()

    await siri.connect()

    async with Client(MQTT.host) as client:
        async with client.filtered_messages(f'{MQTT.domain}/+/out') as messages:
            await client.subscribe(f'{MQTT.domain}/#')
            async for message in messages:
                try:
                    m = json.loads(message.payload.decode())
                except:
                    m = []
                uuid = message.topic.split('/')[1]
                #if not uuid.startswith('455db'):
                #    continue
                ts = int(time.time())
                if 'uptime' in m:
                    #print(uuid, m['uptime'])
                    await siri.insert({f'{uuid}.uptime': [[ts, m['uptime']]]})
                elif 'data' in m:
                    _data = battery.decode(m['data'])
                    #print(uuid, res)
                    print(f'Sending data for {uuid}...')
                    data = {}
                    for kdata, vdata in _data.items():
                        data[f'{uuid}.{kdata.lower()}'] = [[ts, vdata]]

                    #print(data)
                    await siri.insert(data)
    siri.close()


async def action_battery():
    async with Client(MQTT.host) as client:
        for uuid in UUIDS:
            message = 'battery'
            topic = f'{MQTT.domain}/{uuid}/action'
            print(f'[topic="{topic}"] Publishing message={message}')
            await client.publish(topic, message, qos=1)

loop = asyncio.get_event_loop()
loop.run_until_complete(update(siri))
