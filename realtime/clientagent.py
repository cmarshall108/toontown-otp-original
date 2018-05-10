"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, August 17th, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import time

from panda3d.core import UniqueIdAllocator, NetDatagram
from realtime import io, types
from direct.directnotify.DirectNotifyGlobal import directNotify

class Client(io.NetworkHandler):
    notify = directNotify.newCategory('Client')

    def __init__(self, network, rendezvous, address, connection):
        io.NetworkHandler.__init__(self, network, rendezvous, address, connection)

    def setup(self):
        io.NetworkHandler.setup(self)

        if not self.channel:
            self.channel = self.network.channel_allocator.allocate()
            self.register_for_channel(self.channel)

    def handle_send_disconnect(self, error_code, reason):
        datagram = NetDatagram()
        datagram.add_uint16(types.CLIENT_GO_GET_LOST)
        datagram.add_uint16(error_code)
        datagram.add_string(reason)

        self.handle_send_datagram(datagram)
        self.handle_disconnect()

    def handle_datagram(self, di, datagram):
        try:
            message_type = di.get_uint16()
        except:
            return self.handle_disconnect()

        if message_type == types.CLIENT_HEARTBEAT:
            pass
        elif message_type == types.CLIENT_LOGIN_2:
            self.handle_login(di)
        elif message_type == types.CLIENT_GET_SHARD_LIST:
            self.handle_get_shard_list()
        elif message_type == types.CLIENT_DISCONNECT:
            self.handle_disconnect()
        else:
            self.notify.warning('Unknown datagram recieved with message type: %d!' % message_type)

    def handle_internal_datagram(self, message_type, sender, di):
        if message_type == types.STATESERVER_GET_SHARD_ALL_RESP:
            self.handle_get_shard_list_resp(di)
        else:
            self.notify.warning('Unknown internal datagram recieved with message type: %d!' % message_type)

    def handle_login(self, di):
        play_token = di.get_string()
        server_version = di.get_string()
        hash_val = di.get_uint32()
        token_type = di.get_int32()

        # TODO: implement some sort of mongo database account systems
        # using the database server...
        datagram = NetDatagram()
        datagram.add_uint16(types.CLIENT_LOGIN_2_RESP)
        datagram.add_uint8(0)
        datagram.add_string('')
        datagram.add_string(play_token)
        datagram.add_uint8(0)
        datagram.add_uint32(int(time.time()))
        datagram.add_uint32(int(time.clock()))
        datagram.add_uint8(1)
        datagram.add_int32(0)

        self.handle_send_datagram(datagram)

    def handle_get_shard_list(self):
        datagram = NetDatagram()
        datagram.add_uint8(1)
        datagram.add_uint64(types.STATESERVER_CHANNEL)
        datagram.add_uint64(self.channel)
        datagram.add_uint16(types.STATESERVER_GET_SHARD_ALL)
        self.network.handle_send_connection_datagram(datagram)

    def handle_get_shard_list_resp(self, di):
        datagram = NetDatagram()
        datagram.add_uint16(types.CLIENT_GET_SHARD_LIST_RESP)
        datagram.append_data(di.get_remaining_bytes())
        self.handle_send_datagram(datagram)

    def shutdown(self):
        if self.channel:
            self.network.channel_allocator.free(self.channel)
            self.unregister_for_channel(self.channel)

        io.NetworkHandler.shutdown(self)

class ClientAgent(io.NetworkListener, io.NetworkConnector):
    notify = directNotify.newCategory('ClientAgent')

    def __init__(self, address, port, connect_address, connect_port, channel):
        io.NetworkListener.__init__(self, address, port, Client)
        io.NetworkConnector.__init__(self, connect_address, connect_port, channel)

        self.channel_allocator = UniqueIdAllocator(config.GetInt('clientagent-min-channels', 1000000000),
            config.GetInt('clientagent-max-channels', 1009999999))

    def setup(self):
        io.NetworkListener.setup(self)
        io.NetworkConnector.setup(self)

    def handle_datagram(self, sender, message_type, di):
        handler = self.get_handler_from_channel(di.get_uint64())

        if not handler:
            return

        handler.handle_internal_datagram(message_type, sender, di)

    def shutdown(self):
        io.NetworkListener.shutdown(self)
        io.NetworkConnector.shutdown(self)
