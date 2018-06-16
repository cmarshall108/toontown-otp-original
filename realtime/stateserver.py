"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, August 17th, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import random

from panda3d.direct import DCPacker
from realtime import io, types
from game.OtpDoGlobals import *
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

    def get_shard(self, channel):
        if not self.has_shard(channel):
            return None

        return self._shards[channel]

    def get_shards(self):
        return self._shards.values()

class StateObject(object):
    notify = directNotify.newCategory('StateObject')

    def __init__(self, network, do_id, parent_id, zone_id, dc_class, has_other, di):
        self._network = network
        self._do_id = do_id

        self._old_owner_id = 0
        self._owner_id = 0

        self._old_parent_id = 0
        self._parent_id = parent_id

        self._old_zone_id = 0
        self._zone_id = zone_id

        self._dc_class = dc_class
        self._has_other = has_other

        self._required_fields = {}
        self._other_fields = {}

        field_packer = DCPacker()
        field_packer.set_unpack_data(di.get_remaining_bytes())

        for field_index in xrange(self._dc_class.get_num_inherited_fields()):
            field = self._dc_class.get_inherited_field(field_index)

            if not field:
                self.notify.error('Failed to unpack field: %d dclass: %s, unknown field!' % (
                    field_index, self._dc_class.get_name()))

            if field.as_molecular_field() or not field.is_required():
                continue

            field_packer.begin_unpack(field)
            field_args = field.unpack_args(field_packer)
            field_packer.end_unpack()

            self._required_fields[field.get_number()] = field_args

        self._network.register_for_channel(self._do_id)

    @property
    def do_id(self):
        return self._do_id

    @property
    def old_owner_id(self):
        return self._old_owner_id

    @old_owner_id.setter
    def old_owner_id(self, old_owner_id):
        self._old_owner_id = old_owner_id

    @property
    def owner_id(self):
        return self._owner_id

    @owner_id.setter
    def owner_id(self, owner_id):
        self._owner_id = owner_id

    @property
    def old_parent_id(self):
        return self._old_parent_id

    @property
    def parent_id(self):
        return self._parent_id

    @parent_id.setter
    def parent_id(self, parent_id):
        self._parent_id = parent_id

    @property
    def old_zone_id(self):
        return self._old_zone_id

    @property
    def zone_id(self):
        return self._zone_id

    @zone_id.setter
    def zone_id(self, zone_id):
        self._zone_id = zone_id

    @property
    def dc_class(self):
        return self._dc_class

    @property
    def has_other(self):
        return self._has_other

    def append_required_data(self, datagram):
        field_packer = DCPacker()
        for index in self._required_fields:
            field = self._dc_class.get_field_by_index(index)

            if not field:
                self.notify.error('Failed to append required data for field: %s dclass: %s, unknown field' % (
                    field_name, self._dc_class.get_name()))

            field_packer.begin_pack(field)

            if not self._has_other:
                field.pack_args(field_packer, self._required_fields[field.get_number()])
            else:
                field.pack_args(field_packer, self._other_fields[field.get_number()])

            field_packer.end_pack()

        datagram.append_data(field_packer.get_string())

    def setup(self):
        self.handle_send_generate_broadcast()

    def handle_internal_datagram(self, sender, message_type, di):
        if message_type == types.STATESERVER_OBJECT_SET_OWNER:
            self.handle_set_owner(sender, di)
        elif message_type == types.STATESERVER_OBJECT_SET_ZONE:
            self.handle_set_zone(sender, di)

    def handle_set_owner(self, sender, di):
        owner_id = di.get_uint64()

        self._old_owner_id = self._owner_id
        self._owner_id = owner_id

    def handle_set_zone(self, sender, di):
        zone_id = di.get_uint32()

        self._old_parent_id = self._parent_id
        self._old_zone_id = self._zone_id

        self._zone_id = zone_id

        # delete any existing objects within our new interest set,
        # exclude our own object since thats a local object...
        self.handle_delete_objects(excludes=[self.do_id])
        self.handle_send_delete_broadcast(excludes=[self.do_id])

        # send generates for the quite zone objects before we change the avatar's
        # zone so that they always have interest in those objects...
        self.handle_send_generates(quietZone=True, excludes=[self.do_id])

        # if we have an owner, tell them that we've sent all of the initial zone
        # objects in the new interest set...
        self.handle_send_set_zone(self._owner_id, self._zone_id, self._old_zone_id)

        # generate any new objects within our new interest set,
        # exclude our own object since thats a local object...
        self.handle_send_generates(excludes=[self.do_id])
        self.handle_send_generate_broadcast(excludes=[self.do_id])

    def handle_update_field(self, sender, channel, di):
        field_id = di.get_uint16()
        field = self._dc_class.get_field_by_index(field_id)

        if not field:
            self.notify.warning('Failed to update field: %d dclass: %s, unknown field!' % (
                field_id, self._dc_class.get_name()))

            return

        # ensure this field is not a bogus field...
        if field.is_bogus_field():
            self.notify.debug('Cannot handle field update for field: %s dclass: %s, field is bogus!' % (
                field.get_name(), self._dc_class.get_name()))

            return

        if not self._network.shard_manager.has_shard(sender):
            avatar_id = self._network.get_avatar_id_from_connection_channel(sender)

            if not avatar_id:
                self.notify.warning('Cannot handle field update for field: %s dclass: %s, unknown avatar: %d!' % (
                    field.get_name(), self._dc_class.get_name(), avatar_id))

                return

            if field.is_ownsend():
                if sender != self._owner_id:
                    self.notify.warning('Cannot handle field update for field: %s dclass: %s, field not sendable!' % (
                        field.get_name(), self._dc_class.get_name()))

                    return
            else:
                if not field.is_clsend():
                    self.notify.warning('Cannot handle field update for field: %s dclass: %s, field not sendable!' % (
                        field.get_name(), self._dc_class.get_name()))

                    return

            if not field.is_broadcast():
                self.handle_send_update(field, sender, self._parent_id, di)
            else:
                self.handle_send_update_broadcast(field, sender, di, excludes=[avatar_id])
        else:
            if not field.is_broadcast():
                self.handle_send_update(field, self._parent_id, channel, di)
            else:
                self.handle_send_update_broadcast(field, self._parent_id, di, excludes=[self.do_id])

    def handle_send_changing_location(self, channel):
        datagram = io.NetworkDatagram()
        datagram.add_header(channel, self._network.channel,
            types.STATESERVER_OBJECT_CHANGING_LOCATION)

        datagram.add_uint32(self._do_id)
        datagram.add_uint32(self._parent_id)
        datagram.add_uint32(self._zone_id)
        self._network.handle_send_connection_datagram(datagram)

    def handle_send_set_zone(self, channel, zone_id, old_zone_id):
        datagram = io.NetworkDatagram()
        datagram.add_header(channel, self._network.channel,
            types.STATESERVER_OBJECT_SET_ZONE_RESP)

        datagram.add_uint32(old_zone_id)
        datagram.add_uint32(zone_id)
        self._network.handle_send_connection_datagram(datagram)

    def handle_send_update(self, field, sender, channel, di):
        datagram = io.NetworkDatagram()
        datagram.add_header(channel, sender,
            types.STATESERVER_OBJECT_UPDATE_FIELD)

        datagram.add_uint32(self._do_id)
        datagram.add_uint16(field.get_number())

        field_packer = DCPacker()
        field_packer.begin_pack(field)

        if di.get_remaining_size():
            field_packer.pack_literal_value(di.get_remaining_bytes())

        field_packer.end_pack()

        datagram.append_data(field_packer.get_string())
        self._network.handle_send_connection_datagram(datagram)

    def handle_send_update_broadcast(self, field, sender, di, excludes=[]):
        for state_object in self._network.object_manager.state_objects.values():

            if state_object.do_id in excludes:
                continue

            if state_object.parent_id == self._parent_id and state_object.zone_id == self._zone_id:

                if not state_object.owner_id:
                    continue

                self.handle_send_update(field, sender, state_object.owner_id, di)

        if self._do_id in excludes:
            return

        if not self._owner_id:
            self.handle_send_update(field, sender, self._parent_id, di)

    def handle_send_generate(self, channel):
        datagram = io.NetworkDatagram()

        if not self._has_other:
            datagram.add_header(channel, self._network.channel,
                types.STATESERVER_OBJECT_ENTER_LOCATION_WITH_REQUIRED)
        else:
            datagram.add_header(channel, self._network.channel,
                types.STATESERVER_OBJECT_ENTER_LOCATION_WITH_REQUIRED_OTHER)

        datagram.add_uint64(self.do_id)
        datagram.add_uint64(self.parent_id)
        datagram.add_uint32(self.zone_id)
        datagram.add_uint16(self.dc_class.get_number())

        self.append_required_data(datagram)
        self._network.handle_send_connection_datagram(datagram)

    def handle_send_generate_broadcast(self, excludes=[]):
        for state_object in self._network.object_manager.state_objects.values():

            if state_object.do_id in excludes:
                continue

            if state_object.parent_id == self._parent_id and state_object.zone_id == self._zone_id:

                if not state_object.owner_id:
                    continue

                self.handle_send_generate(state_object.owner_id)

    def handle_send_generates(self, quietZone=False, excludes=[]):
        for state_object in self._network.object_manager.state_objects.values():

            if state_object.do_id in excludes:
                continue

            if state_object.zone_id == OTP_ZONE_ID_OLD_QUIET_ZONE and not quietZone:
                continue

            if state_object.parent_id == self._parent_id and state_object.zone_id == self._zone_id:
                state_object.handle_send_generate(self._owner_id)

    def handle_send_delete(self, channel):
        datagram = io.NetworkDatagram()
        datagram.add_header(channel, self._network.channel,
            types.STATESERVER_OBJECT_DELETE_RAM)

        datagram.add_uint64(self.do_id)
        self._network.handle_send_connection_datagram(datagram)

    def handle_send_delete_broadcast(self, excludes=[]):
        for state_object in self._network.object_manager.state_objects.values():

            if state_object.do_id in excludes:
                continue

            if state_object.parent_id == self._old_parent_id and state_object.zone_id == self._old_zone_id:

                if not state_object.owner_id:
                    continue

                self.handle_send_delete(state_object.owner_id)

    def handle_delete_objects(self, excludes=[]):
        for state_object in self._network.object_manager.state_objects.values():

            if state_object.do_id in excludes:
                continue

            if state_object.zone_id == OTP_ZONE_ID_OLD_QUIET_ZONE:
                continue

            if state_object.parent_id == self._old_parent_id and state_object.zone_id == self._old_zone_id:
                state_object.handle_send_delete(self._owner_id)

    def shutdown(self):
        self.handle_send_delete_broadcast()

class StateObjectManager(object):
    notify = directNotify.newCategory('StateObjectManager')

    def __init__(self):
        self._state_objects = {}

    @property
    def state_objects(self):
        return self._state_objects

    def has_state_object(self, do_id):
        return do_id in self._state_objects

    def add_state_object(self, state_object):
        if self.has_state_object(state_object.do_id):
            return

        self._state_objects[state_object.do_id] = state_object
        state_object.setup()

    def remove_state_object(self, state_object):
        if not self.has_state_object(state_object.do_id):
            return

        state_object.shutdown()
        del self._state_objects[state_object.do_id]

    def get_state_object(self, do_id):
        return self._state_objects.get(do_id)

class StateServer(io.NetworkConnector):
    notify = directNotify.newCategory('StateServer')

    def __init__(self, *args, **kwargs):
        io.NetworkConnector.__init__(self, *args, **kwargs)

        self._shard_manager = ShardManager()
        self._object_manager = StateObjectManager()

    @property
    def shard_manager(self):
        return self._shard_manager

    @property
    def object_manager(self):
        return self._object_manager

    def handle_datagram(self, channel, sender, message_type, di):
        if message_type == types.STATESERVER_ADD_SHARD:
            self.handle_add_shard(sender, di)
        elif message_type == types.STATESERVER_REMOVE_SHARD:
            self.handle_remove_shard(sender)
        elif message_type == types.STATESERVER_GET_SHARD_ALL:
            self.handle_get_shard_list(sender, di)
        elif message_type == types.STATESERVER_OBJECT_GENERATE_WITH_REQUIRED:
            self.handle_generate(sender, False, di)
        elif message_type == types.STATESERVER_OBJECT_GENERATE_WITH_REQUIRED_OTHER:
            self.handle_generate(sender, True, di)
        elif message_type == types.STATESERVER_OBJECT_UPDATE_FIELD:
            self.handle_object_update_field(sender, channel, di)
        elif message_type == types.STATESERVER_SET_AVATAR:
            self.handle_set_avatar(sender, di)
        else:
            state_object = self._object_manager.get_state_object(channel)

            if not state_object:
                self.notify.debug('Received an unknown message type: %d from channel: %d!' % (
                    message_type, sender))

                return

            state_object.handle_internal_datagram(sender, message_type, di)

    def handle_add_shard(self, sender, di):
        self._shard_manager.add_shard(sender, di.getString(), di.get_uint32())

    def handle_remove_shard(self, sender):
        shard = self._shard_manager.get_shard(sender)

        if not shard:
            self.notify.warning('Cannot remove shard: %d, does not exist!' % (
                sender))

            return

        for state_object in self._object_manager.state_objects.values():

            if state_object.parent_id == shard.channel:
                self._object_manager.remove_state_object(state_object)

        self._shard_manager.remove_shard(shard.channel)

    def handle_get_shard_list(self, sender, di):
        datagram = io.NetworkDatagram()
        datagram.add_header(sender, self.channel,
            types.STATESERVER_GET_SHARD_ALL_RESP)

        datagram.add_uint16(len(self._shard_manager.shards))

        for shard in self._shard_manager.get_shards():
            datagram.add_uint32(shard.channel)
            datagram.add_string(shard.name)
            datagram.add_uint32(shard.population)

        self.handle_send_connection_datagram(datagram)

    def handle_generate(self, sender, has_other, di):
        do_id = di.get_uint32()
        parent_id = di.get_uint32()
        zone_id = di.get_uint32()
        dc_id = di.get_uint16()

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

    def handle_object_update_field(self, sender, channel, di):
        do_id = di.get_uint32()

        if not di.get_remaining_size():
            self.notify.warning('Cannot handle an field update for object: %d, truncated datagram!' % (
                do_id))

            return

        state_object = self._object_manager.get_state_object(do_id)

        if not state_object:
            self.notify.warning('Cannot handle an field update for object: %d, unknown object!' % (
                do_id))

            return

        state_object.handle_update_field(sender, channel, di)

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

        avatar_object = StateObject(self, do_id, parent_id, zone_id, dc_class, False, di)
        self._object_manager.add_state_object(avatar_object)

        # tell the AI which has been chosen to generate the avatar on,
        # that the avatar has been created and the client is awaiting it's response...
        datagram = io.NetworkDatagram()
        datagram.add_header(parent_id, sender,
            types.STATESERVER_SET_AVATAR_RESP)

        datagram.add_uint32(do_id)
        datagram.add_uint32(parent_id)
        datagram.add_uint32(zone_id)

        avatar_object.append_required_data(datagram)
        self.handle_send_connection_datagram(datagram)
