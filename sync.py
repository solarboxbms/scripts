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
from config import SIRIDB, MQTT, DEVICES, UUIDS

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
        for uuid in UUIDS.keys():
            message = 'battery'
            topic = f'{MQTT.domain}/{uuid}/action'
            print(f'[topic="{topic}"] Publishing message={message}')
            await client.publish(topic, message, qos=1)

loop = asyncio.get_event_loop()
loop.run_until_complete(update(siri))
