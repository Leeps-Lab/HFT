"""
Client for simple Ouch Server
"""

import sys
import asyncio
import asyncio.streams
import configargparse
import logging as log
# import binascii
from random import randrange, randint
import itertools

from OuchServer.ouch_messages import OuchClientMessages, OuchServerMessages

p = configargparse.ArgParser()
p.add('--port', default=12345)
p.add('--host', default='127.0.0.1', help="Address of server")
options, args = p.parse_known_args()



class Client():
    def __init__(self):
        self.reader = None
        self.writer = None

    async def recv(self):
        try:
            header = (await self.reader.readexactly(1))
        except asyncio.IncompleteReadError:
            log.error('connection terminated without response')
            return None
        log.debug('Received Ouch header as binary: %r', header)
        log.debug('bytes: %r', list(header))
        message_type = OuchServerMessages.lookup_by_header_bytes(header)
        try:
            payload = (await self.reader.readexactly(message_type.payload_size))
        except asyncio.IncompleteReadError as err:
            log.error('Connection terminated mid-packet!')
            return None
        log.debug('Received Ouch payload as binary: %r', payload)
        log.debug('bytes: %r', list(payload))

        response_msg = message_type.from_bytes(payload, header=False)
        return response_msg

    async def recver(self, loop):
        if self.reader is None:
            reader, writer = await asyncio.streams.open_connection(
            options.host, 
            options.port, 
            loop=loop)
            self.reader = reader
            self.writer = writer
          
        for index in itertools.count():
            response = await self.recv()
            if index % 1000 ==0:
                print('received {} messages'.format(index))
            #log.info('Received msg %s', response)
            #response = await recv()
            #print('recv message: ', response)
            #log.debug("Received response Ouch message: %s", response)

    async def send(self, request):
        self.writer.write(bytes(request))
        await self.writer.drain()

    async def sender(self, loop):
        if self.reader is None:
            reader, writer = await asyncio.streams.open_connection(
            options.host, 
            options.port, 
            loop=loop)
            self.reader = reader
            self.writer = writer

        for index in itertools.count():
            request = OuchClientMessages.EnterOrder(
                order_token='{:014d}'.format(index).encode('ascii'),
                buy_sell_indicator=b'B' if randint(0,1)==1 else b'S',
                shares=randrange(1,10**6-1),
                stock=b'AMAZGOOG',
                price=randrange(1,100),
                time_in_force=randrange(0,99999),
                firm=b'OUCH',
                display=b'N',
                capacity=b'O',
                intermarket_sweep_eligibility=b'N',
                minimum_quantity=1,
                cross_type=b'N',
                customer_type=b' ')
            #print('send message: ', request)
            #log.info("Sending Ouch message: %s", request)
            await self.send(request)
            if index % 1000 == 0:
                print('sent {} messages'.format(index))   
            await asyncio.sleep(0.0001) 

    async def start(self, loop):
        reader, writer = await asyncio.streams.open_connection(
            options.host, 
            options.port, 
            loop=loop)
        self.reader = reader
        self.writer = writer
        await self.sender()
        writer.close()
        await asyncio.sleep(0.5)


def main():
    log.basicConfig(level=log.INFO)
    log.debug(options)

    client = Client()
    loop = asyncio.get_event_loop()
    # creates a client and connects to our server
    asyncio.ensure_future(client.sender(loop), loop = loop)
    asyncio.ensure_future(client.recver(loop), loop = loop)

    try:
        loop.run_forever()       
    finally:
        loop.close()

if __name__ == '__main__':
    main()
