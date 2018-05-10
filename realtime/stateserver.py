"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, August 17th, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

from panda3d.core import NetDatagram
from realtime import io, types
from direct.directnotify.DirectNotifyGlobal import directNotify

class Shard(object):

    def __init__(self, channel, name, population):
        self.channel = channel
        self.name = name
        self.population = population

class ShardManager(object):

    def __init__(self):
        self.shards = {}

    def has_shard(self, channel):
        return channel in self.shards

    def add_shard(self, channel, name, population):
        if self.has_shard(channel):
            return

        self.shards[channel] = Shard(channel, name, population)

    def remove_shard(self, channel):
        if not self.has_shard(channel):
            return

        del self.shards[channel]

    def get_shards(self):
        return self.shards.values()

class StateServer(io.NetworkConnector):
    notify = directNotify.newCategory('StateServer')

    def __init__(self, address, port, channel):
        io.NetworkConnector.__init__(self, address, port, channel)

        self.shard_manager = ShardManager()

    def handle_datagram(self, sender, message_type, di):
        if message_type == types.STATESERVER_ADD_SHARD:
            self.handle_add_shard(sender, di)
        elif message_type == types.STATESERVER_REMOVE_SHARD:
            self.handle_remove_shard(sender)
        elif message_type == types.STATESERVER_GET_SHARD_ALL:
            self.handle_get_shard_list(sender, di)

    def handle_add_shard(self, sender, di):
        self.shard_manager.add_shard(sender, di.getString(), di.get_uint32())

    def handle_remove_shard(self, sender):
        self.shard_manager.remove_shard(sender)

    def handle_get_shard_list(self, sender, di):
        datagram = NetDatagram()
        datagram.add_uint8(1)
        datagram.add_uint64(sender)
        datagram.add_uint64(self.channel)
        datagram.add_uint16(types.STATESERVER_GET_SHARD_ALL_RESP)
        datagram.add_uint64(sender)
        datagram.add_uint16(len(self.shard_manager.shards))

        for shard in self.shard_manager.get_shards():
            datagram.add_uint32(shard.channel)
            datagram.add_string(shard.name)
            datagram.add_uint32(shard.population)

        self.handle_send_connection_datagram(datagram)
