"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, August 17th, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import random

from panda3d.direct import DCPacker
from realtime import io, types
from direct.directnotify.DirectNotifyGlobal import directNotify

class Shard(object):

    def __init__(self, channel, name, population):
        self.channel = channel
        self.name = name
        self.population = population

class ShardManager(object):

    def __init__(self):
        self._shards = {}

    @property
    def shards(self):
        return self._shards

    def has_shard(self, channel):
        return channel in self._shards

    def add_shard(self, channel, name, population):
        if self.has_shard(channel):
            return

        self._shards[channel] = Shard(channel, name, population)

    def remove_shard(self, channel):
        if not self.has_shard(channel):
            return

        del self._shards[channel]

    def get_shards(self):
        return self._shards.values()

class StateObject(object):
    notify = directNotify.newCategory('StateObject')

    def __init__(self, network, do_id, parent_id, zone_id, dc_class, has_other, di):
        self._network = network
        self._do_id = do_id
        self._parent_id = parent_id
        self._zone_id = zone_id
        self._dc_class = dc_class
        self._has_other = has_other
        self._required_fields = {}

        for index in xrange(self._dc_class.get_num_fields()):
            field = self._dc_class.get_field_by_index(index)

            if not field:
                continue

            if not field.as_atomic_field() or not field.is_required():
                continue

            self._required_fields[field.get_number()] = field.get_default_value()

        self._network.register_for_channel(self._do_id)

    @property
    def do_id(self):
        return self._do_id

    @property
    def parent_id(self):
        return self._parent_id

    @property
    def zone_id(self):
        return self._zone_id

    @property
    def dc_class(self):
        return self._dc_class

    @property
    def has_other(self):
        return self._has_other

    def append_required_data(self, datagram):
        dc_packer = DCPacker()
        for index in self._required_fields:
            field = self._dc_class.get_field_by_index(index)

            if not field:
                self.notify.error('Failed to append required data for field: %s dclass: %s, unknown field' % (
                    field_name, self._dc_class.get_name()))

            dc_packer.begin_pack(field)
            dc_packer.pack_literal_value(self._required_fields[index])
            dc_packer.end_pack()

        datagram.append_data(dc_packer.get_string())

class StateObjectManager(object):
    notify = directNotify.newCategory('StateObjectManager')

    def __init__(self):
        self._state_objects = {}

    def has_state_object(self, do_id):
        return do_id in self._state_objects

    def add_state_object(self, state_object):
        if self.has_state_object(state_object.do_id):
            return

        self._state_objects[state_object.do_id] = state_object

    def remove_state_object(self, state_object):
        if not self.has_state_object(state_object.do_id):
            return

        del self._state_objects[state_object.do_id]

    def get_state_object(self, do_id):
        return self._state_objects.get(do_id)

class StateServer(io.NetworkConnector):
    notify = directNotify.newCategory('StateServer')

    def __init__(self, *args, **kwargs):
        io.NetworkConnector.__init__(self, *args, **kwargs)

        self._shard_manager = ShardManager()
        self._object_manager = StateObjectManager()

    def handle_datagram(self, channel, sender, message_type, di):
        if message_type == types.STATESERVER_ADD_SHARD:
            self.handle_add_shard(sender, di)
        elif message_type == types.STATESERVER_REMOVE_SHARD:
            self.handle_remove_shard(sender)
        elif message_type == types.STATESERVER_GET_SHARD_ALL:
            self.handle_get_shard_list(sender, di)
        elif message_type == types.STATESERVER_OBJECT_GENERATE_WITH_REQUIRED:
            self.handle_generate(False, dgi)
        elif message_type == types.STATESERVER_OBJECT_GENERATE_WITH_REQUIRED_OTHER:
            self.handle_generate(True, dgi)
        elif message_type == types.STATESERVER_SET_AVATAR:
            self.handle_set_avatar(sender, di)

    def handle_add_shard(self, sender, di):
        self._shard_manager.add_shard(sender, di.getString(), di.get_uint32())

    def handle_remove_shard(self, sender):
        self._shard_manager.remove_shard(sender)

    def handle_get_shard_list(self, sender, di):
        datagram = io.NetworkDatagram()
        datagram.add_header(sender, self.channel, types.STATESERVER_GET_SHARD_ALL_RESP)
        datagram.add_uint16(len(self._shard_manager.shards))

        for shard in self._shard_manager.get_shards():
            datagram.add_uint32(shard.channel)
            datagram.add_string(shard.name)
            datagram.add_uint32(shard.population)

        self.handle_send_connection_datagram(datagram)

    def handle_generate(self, has_other, di):
        do_id = dgi.get_uint32()
        parent_id = dgi.get_uint32()
        zone_id = dgi.get_uint32()
        dc_id = dgi.get_uint16()

        if self._object_manager.has_state_object(do_id):
            self.notify.debug("Failed to generate an already existing object with do_id: %d!" % (
                do_id))

            return

        dc_class = self.dc_loader.dclasses_by_number.get(dc_id)

        if not dc_class:
            self.notify.warning("Failed to generate an object with do_id: %d, no dclass found for dc_id: %d!" % (
                do_id, dc_id))

            return

        state_object = StateObject(self, do_id, parent_id, zone_id, dc_class, has_other, di)
        self._object_manager.add_state_object(state_object)

    def handle_set_avatar(self, sender, di):
        # ensure the sender of this message was not a shard channel,
        # only client agent's should send this message...
        if self._shard_manager.has_shard(sender):
            return

        # we are generating a new avatar, this is a "special" method in which will
        # create a distributed object and respond to the client with the default
        # fields specified by the toon's dclass fields...
        do_id = di.get_uint32()
        parent_id = random.choice(self._shard_manager.shards.keys())
        zone_id = 0
        dc_class = self.dc_loader.dclasses_by_name['DistributedToon']

        avatar_object = StateObject(self, do_id, parent_id, zone_id, dc_class, True, di)
        self._object_manager.add_state_object(avatar_object)

        # tell the AI which has been chosen to generate the avatar on,
        # that the avatar has been created and the client is awaiting it's response...
        datagram = io.NetworkDatagram()
        datagram.add_header(parent_id, sender, types.STATESERVER_SET_AVATAR_RESP)
        datagram.add_uint32(do_id)
        datagram.add_uint32(parent_id)
        datagram.add_uint32(zone_id)
        avatar_object.append_required_data(datagram)
        self.handle_send_connection_datagram(datagram)
