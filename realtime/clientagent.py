"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, August 17th, 2017
 * Contributed to by Prince Frizzy <theclashingfritz@gmail.com>, May 12th, 2018
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import time
import semidbm

from panda3d.core import UniqueIdAllocator
from realtime import io, types
from direct.directnotify.DirectNotifyGlobal import directNotify
from direct.fsm.FSM import FSM

class ClientOperation(FSM):
    notify = directNotify.newCategory('ClientOperation')

    def __init__(self, manager, client, callback):
        FSM.__init__(self, self.__class__.__name__)

        self._manager = manager
        self._client = client
        self._callback = callback

    @property
    def manager(self):
        return self._manager

    @property
    def client(self):
        return self._client

    @property
    def callback(self):
        return self._callback

    @callback.setter
    def callback(self, callback):
        self._callback = callback

    def enterOff(self):
        pass

    def exitOff(self):
        pass

    def defaultFilter(self, request, *args):
        return FSM.defaultFilter(self, request, *args)

class ClientOperationManager(object):
    notify = directNotify.newCategory('ClientOperationManager')

    def __init__(self, network):
        self._network = network
        self._channel2fsm = {}

    @property
    def network(self):
        return self._network

    @property
    def channel2fsm(self):
        return self._channel2fsm

    def has_fsm(self, channel):
        return channel in self._channel2fsm

    def add_fsm(self, channel, fsm):
        if self.has_fsm(channel):
            return

        self._channel2fsm[channel] = fsm

    def remove_fsm(self, channel):
        if not self.has_fsm(channel):
            return

        del self._channel2fsm[channel]

    def get_fsm(self, channel):
        return self._channel2fsm.get(channel)

    def run_operation(self, fsm, client, callback, *args, **kwargs):
        if self.has_fsm(client.channel):
            self.notify.warning('Cannot run operation: %s for channel %d, operation already running!' % (
                fsm.__name__, client.channel))

            return None

        operation = fsm(self, client, callback, *args, **kwargs)
        self.add_fsm(client.channel, operation)
        return operation

    def stop_operation(self, client):
        if not self.has_fsm(client.channel):
            self.notify.warning('Cannot stop operation for channel %d, unknown operation!' % (
                client.channel))

            return

        operation = self.get_fsm(client.channel)
        operation.demand('Off')

        self.remove_fsm(client.channel)

class LoadAccountFSM(ClientOperation):
    notify = directNotify.newCategory('LoadAccountFSM')

    def __init__(self, manager, client, callback, play_token):
        ClientOperation.__init__(self, manager, client, callback)

        self._play_token = play_token

    def enterLoad(self):
        if self._play_token not in self.manager.dbm:
            self.demand('Create')
            return

        account_id = int(self.manager.dbm[self._play_token])

        self.manager.network.database_interface.query_object(self.client.channel, types.DATABASE_CHANNEL, account_id,
            lambda dclass, fields: self.__account_loaded(account_id, dclass, fields),
            self.manager.network.dc_loader.dclasses_by_name['Account'])

    def __account_loaded(self, account_id, dclass, fields):
        if not dclass and not fields:
            self.notify.warning('Failed to load account: %d for channel: %d playtoken: %s!' % (
                account_id, self._client.channel, self._play_token))

            return

        self.request('SetAccount', account_id)

    def exitLoad(self):
        pass

    def enterCreate(self):
        fields = {
            'ACCOUNT_AV_SET': ([0] * 6,),
            'BIRTH_DATE': ('',),
            'BLAST_NAME': (self._play_token,),
            'CREATED': (time.ctime(),),
            'FIRST_NAME': ('',),
            'LAST_LOGIN': ('',),
            'LAST_NAME': ('',),
            'PLAYED_MINUTES': ('',),
            'PLAYED_MINUTES_PERIOD': ('',),
            'HOUSE_ID_SET': ([0] * 6,),
            'ESTATE_ID': (0,)
        }

        self.manager.network.database_interface.create_object(self.client.channel, types.DATABASE_CHANNEL,
            self.manager.network.dc_loader.dclasses_by_name['Account'], fields=fields,
            callback=self.__account_created)

    def __account_created(self, account_id):
        if not account_id:
            self.notify.warning('Failed to create account for channel: %d playtoken: %s!' % (
                self._client.channel, self._play_token))

            return

        self.manager.dbm[self._play_token] = str(account_id)
        self.request('SetAccount', account_id)

    def exitCreate(self):
        pass

    def enterSetAccount(self, account_id):
        # the server says our login request was successful,
        # it is now ok to mark the client as authenticated...
        self._client.authenticated = True

        # TODO: FIXME!
        self._client.channel_alias = account_id
        self._client.register_for_channel(account_id)

        # we're all done.
        self.ignoreAll()
        self.manager.stop_operation(self._client)

        # call the callback our client object has specified,
        # this will notify the game client of the successful login...
        self._callback()

    def exitSetAccount(self):
        pass

class ClientAvatarData(object):

    def __init__(self, do_id, name_list, dna, position, name_index):
        self._do_id = do_id
        self._name_list = name_list
        self._dna = dna
        self._position = position
        self._name_index = name_index

    @property
    def do_id(self):
        return self._do_id

    @do_id.setter
    def do_id(self, do_id):
        self._do_id = do_id

    @property
    def name_list(self):
        return self._name_list

    @name_list.setter
    def name_list(self, name_list):
        self._name_list = name_list

    @property
    def dna(self):
        return self._dna

    @dna.setter
    def dna(self, dna):
        self._dna = dna

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, position):
        self._position = position

    @property
    def name_index(self):
        return self._name_index

    @name_index.setter
    def name_index(self, name_index):
        self._name_index = name_index

class RetrieveAvatarsFSM(ClientOperation):
    notify = directNotify.newCategory('RetrieveAvatarsFSM')

    def __init__(self, manager, client, callback, account_id):
        ClientOperation.__init__(self, manager, client, callback)

        self._account_id = account_id
        self._pending_avatars = []
        self._avatar_fields = {}

    def enterLoad(self):
        self.manager.network.database_interface.query_object(self.client.channel,
            types.DATABASE_CHANNEL,
            self._account_id,
            lambda dclass, fields: self.__account_loaded(dclass, fields),
            self.manager.network.dc_loader.dclasses_by_name['Account'])

    def exitLoad(self):
        pass

    def __account_loaded(self, dclass, fields):
        avatar_list = fields['ACCOUNT_AV_SET'][0]

        for avatar_id in avatar_list:

            if not avatar_id:
                continue

            self._pending_avatars.append(avatar_id)

            def response(dclass, fields, avatar_id=avatar_id):
                self._avatar_fields[avatar_id] = fields
                self._pending_avatars.remove(avatar_id)
                if not self._pending_avatars:
                    self.request('SetAvatars')

            self.manager.network.database_interface.query_object(self.client.channel,
                types.DATABASE_CHANNEL,
                avatar_id,
                response,
                self.manager.network.dc_loader.dclasses_by_name['DistributedToon'])

        if not self._pending_avatars:
            self.request('SetAvatars')

    def enterSetAvatars(self):
        avatar_list = []

        for avatar_id, fields in self._avatar_fields.items():
            avatar_data = ClientAvatarData(avatar_id, ['', '', '', ''], fields['setDNAString'][0],
                fields['setPosIndex'][0], 0)

            avatar_list.append(avatar_data)

        self._callback(avatar_list)

        # we're all done.
        self.ignoreAll()
        self.manager.stop_operation(self._client)

    def exitSetAvatars(self):
        pass

class CreateAvatarFSM(ClientOperation):
    notify = directNotify.newCategory('CreateAvatarFSM')

    def __init__(self, manager, client, callback, account_id, dna_string, index):
        ClientOperation.__init__(self, manager, client, callback)

        self._account_id = account_id
        self._dna_string = dna_string
        self._index = index

    def enterCreate(self):
        fields = {
            'setDNAString': (self._dna_string,),
            'setPosIndex': (self._index,)
        }

        self.manager.network.database_interface.create_object(self.client.channel,
            types.DATABASE_CHANNEL,
            self.manager.network.dc_loader.dclasses_by_name['DistributedToon'],
            fields=fields,
            callback=lambda avatar_id: self.__avatar_created(avatar_id, self._index))

    def __avatar_created(self, avatar_id, index):
        self.manager.network.database_interface.query_object(self.client.channel,
            types.DATABASE_CHANNEL,
            self._account_id,
            lambda dclass, fields: self.__account_loaded(dclass, fields, avatar_id, index),
            self.manager.network.dc_loader.dclasses_by_name['Account'])

    def __account_loaded(self, dclass, fields, avatar_id, index):
        avatar_list = fields['ACCOUNT_AV_SET'][0]
        avatar_list[index] = avatar_id

        new_fields = {
            'ACCOUNT_AV_SET': (avatar_list,)
        }

        self.manager.network.database_interface.update_object(self.client.channel,
            types.DATABASE_CHANNEL,
            self._account_id,
            self.manager.network.dc_loader.dclasses_by_name['Account'],
            new_fields)

    def exitCreate(self):
        pass

class LoadAvatarFSM(ClientOperation):
    notify = directNotify.newCategory('LoadAvatarFSM')

    def __init__(self, manager, client, callback, avatar_id):
        ClientOperation.__init__(self, manager, client, callback)

        self._avatar_id = avatar_id
        self._dclass = None
        self._fields = {}

    def enterQuery(self):

        def response(dclass, fields):
            self._dclass = dclass
            self._fields = fields
            self.request('Activate')

        self.manager.network.database_interface.query_object(self.client.channel,
            types.DATABASE_CHANNEL,
            self._avatar_id,
            response,
            self.manager.network.dc_loader.dclasses_by_name['DistributedToon'])

    def exitQuery(self):
        pass

    def enterActivate(self):
        datagram = io.NetworkDatagram()
        datagram.add_header(types.STATESERVER_CHANNEL, self._client.channel,
            types.STATESERVER_SET_AVATAR)

        datagram.add_uint32(self._avatar_id)
        self.manager.network.handle_send_connection_datagram(datagram)

        # TODO: FIXME!
        self._client.channel_alias = self._avatar_id
        self._client.register_for_channel(self._avatar_id)

        datagram = io.NetworkDatagram()
        datagram.add_header(self._avatar_id, self._client.channel,
            types.STATESERVER_OBJECT_SET_OWNER)

        datagram.add_uint64(self._client.channel)
        self.manager.network.handle_send_connection_datagram(datagram)

    def exitActivate(self):
        pass

class ClientAccountManager(ClientOperationManager):
    notify = directNotify.newCategory('ClientAccountManager')

    def __init__(self, *args, **kwargs):
        ClientOperationManager.__init__(self, *args, **kwargs)

        self._dbm = semidbm.open(config.GetString('clientagent-dbm-filename', 'databases/database.dbm'),
            config.GetString('clientagent-dbm-mode', 'c'))

    @property
    def dbm(self):
        return self._dbm

    def handle_login(self, client, callback, play_token):
        operation = self.run_operation(LoadAccountFSM, client,
            callback, play_token)

        if not operation:
            return

        operation.request('Load')

    def handle_retrieve_avatars(self, client, callback, account_id):
        operation = self.run_operation(RetrieveAvatarsFSM, client,
            callback, account_id)

        if not operation:
            return

        operation.request('Load')

    def handle_create_avatar(self, client, callback, account_id, dna_string, index):
        operation = self.run_operation(CreateAvatarFSM, client,
            callback, account_id, dna_string, index)

        if not operation:
            return

        operation.request('Create')

    def handle_set_avatar(self, client, callback, avatar_id):
        operation = self.run_operation(LoadAvatarFSM, client,
            callback, avatar_id)

        if not operation:
            return

        operation.request('Query')

class Client(io.NetworkHandler):
    notify = directNotify.newCategory('Client')

    def __init__(self, *args, **kwargs):
        io.NetworkHandler.__init__(self, *args, **kwargs)

        self.channel = self.network.channel_allocator.allocate()

        # TODO: replace this with a dynamic list of owned channels which are,
        # registered with the md (account_id, avatar_id etc...)
        self._channel_alias = None

        self._authenticated = False

    @property
    def channel_alias(self):
        return self._channel_alias

    @channel_alias.setter
    def channel_alias(self, channel_alias):
        self._channel_alias = channel_alias

    @property
    def authenticated(self):
        return self._authenticated

    @authenticated.setter
    def authenticated(self, authenticated):
        self._authenticated = authenticated

    def startup(self):
        io.NetworkHandler.startup(self)

    def handle_send_disconnect(self, code, reason):
        self.notify.warning('Disconnecting channel: %d, reason: %s' % (
            self.channel, reason))

        datagram = io.NetworkDatagram()
        datagram.add_uint16(types.CLIENT_GO_GET_LOST)
        datagram.add_uint16(code)
        datagram.add_string(reason)

        self.handle_send_datagram(datagram)
        self.handle_disconnect()

    def handle_datagram(self, di):
        try:
            message_type = di.get_uint16()
        except:
            return self.handle_disconnect()

        if message_type == types.CLIENT_HEARTBEAT:
            pass
        elif message_type == types.CLIENT_LOGIN_2:
            self.handle_login(di)
        elif message_type == types.CLIENT_DISCONNECT:
            self.handle_disconnect()
        else:
            if not self._authenticated:
                self.handle_send_disconnect(types.CLIENT_DISCONNECT_INVALID_MSGTYPE, 'Cannot send datagram with message type: %d, channel: %d not yet authenticated!' % (
                    message_type, self.channel))

                return
            else:
                self.handle_authenticated_datagram(message_type, di)

    def handle_authenticated_datagram(self, message_type, di):
        if message_type == types.CLIENT_GET_SHARD_LIST:
            self.handle_get_shard_list()
        elif message_type == types.CLIENT_GET_AVATARS:
            self.handle_get_avatars()
        elif message_type == types.CLIENT_CREATE_AVATAR:
            self.handle_create_avatar(di)
        elif message_type == types.CLIENT_SET_AVATAR:
            self.handle_set_avatar(di)
        elif message_type == types.CLIENT_SET_WISHNAME:
            self.handle_set_wishname(di)
        elif message_type == types.CLIENT_SET_NAME_PATTERN:
            self.handle_set_name_pattern(di)
        elif message_type == types.CLIENT_GET_FRIEND_LIST:
            pass
        elif message_type == types.CLIENT_SET_SHARD:
            self.handle_set_shard(di)
        elif message_type == types.CLIENT_SET_ZONE:
            self.handle_set_zone(di)
        elif message_type == types.CLIENT_OBJECT_UPDATE_FIELD:
            self.handle_object_update_field(di)
        else:
            self.handle_send_disconnect(types.CLIENT_DISCONNECT_INVALID_MSGTYPE, 'Unknown datagram: %d from channel: %d!' % (
                message_type, self.channel))

            return

    def handle_internal_datagram(self, message_type, sender, di):
        if message_type == types.STATESERVER_GET_SHARD_ALL_RESP:
            self.handle_get_shard_list_resp(di)
        elif message_type == types.CLIENT_GET_AVATAR_DETAILS_RESP:
            self.handle_avatar_details_resp(di)
        elif message_type == types.STATESERVER_OBJECT_SET_ZONE_RESP:
            self.handle_set_zone_resp(di)
        elif message_type == types.STATESERVER_OBJECT_ENTER_LOCATION_WITH_REQUIRED:
            self.handle_object_enter_location(False, di)
        elif message_type == types.STATESERVER_OBJECT_ENTER_LOCATION_WITH_REQUIRED_OTHER:
            self.handle_object_enter_location(True, di)
        else:
            self.network.database_interface.handle_datagram(message_type, di)

    def handle_login(self, di):
        try:
            play_token = di.get_string()
            server_version = di.get_string()
            hash_val = di.get_uint32()
            token_type = di.get_int32()
        except:
            return self.handle_disconnect()

        if server_version != self.network.server_version:
            self.handle_send_disconnect(types.CLIENT_DISCONNECT_BAD_VERSION, 'Invalid server version: %s, expected: %s!' % (
                server_version, self.network.server_version))

            return

        if token_type != types.CLIENT_LOGIN_2_BLUE:
            self.handle_send_disconnect(types.CLIENT_DISCONNECT_INVALID_PLAY_TOKEN_TYPE, 'Invalid play token type: %d!' % (
                token_type))

            return

        self.network.account_manager.handle_login(self, lambda: self.__handle_login_resp(
            play_token), play_token)

    def __handle_login_resp(self, play_token):
        datagram = io.NetworkDatagram()
        datagram.add_uint16(types.CLIENT_LOGIN_2_RESP)
        datagram.add_uint8(0)
        datagram.add_string('All Ok')
        datagram.add_string(play_token)
        datagram.add_uint8(1)
        datagram.add_uint32(int(time.time()))
        datagram.add_uint32(int(time.clock()))
        datagram.add_uint8(1)
        datagram.add_int32(1000 * 60 * 60)
        self.handle_send_datagram(datagram)

    def handle_get_shard_list(self):
        datagram = io.NetworkDatagram()
        datagram.add_header(types.STATESERVER_CHANNEL, self.channel, types.STATESERVER_GET_SHARD_ALL)
        self.network.handle_send_connection_datagram(datagram)

    def handle_get_shard_list_resp(self, di):
        datagram = io.NetworkDatagram()
        datagram.add_uint16(types.CLIENT_GET_SHARD_LIST_RESP)
        datagram.append_data(di.get_remaining_bytes())
        self.handle_send_datagram(datagram)

    def handle_get_avatars(self):
        self.network.account_manager.handle_retrieve_avatars(self, self.__handle_retrieve_avatars_resp,
            self._channel_alias)

    def __handle_retrieve_avatars_resp(self, avatar_data):
        datagram = io.NetworkDatagram()
        datagram.add_uint16(types.CLIENT_GET_AVATARS_RESP)
        datagram.add_uint8(0)
        datagram.add_uint16(len(avatar_data))

        for avatar in avatar_data:
            datagram.add_uint32(avatar.do_id)
            datagram.add_string(avatar.name_list[0])
            datagram.add_string(avatar.name_list[1])
            datagram.add_string(avatar.name_list[2])
            datagram.add_string(avatar.name_list[3])
            datagram.add_string(avatar.dna)
            datagram.add_uint8(avatar.position)
            datagram.add_uint8(avatar.name_index)

        self.handle_send_datagram(datagram)

    def handle_create_avatar(self, di):
        try:
            echo_context = di.get_uint16()
            dna_string = di.get_string()
            index = di.get_uint8()

            datagram = io.NetworkDatagram()
            datagram.add_uint16(types.CLIENT_CREATE_AVATAR_RESP)
            datagram.add_uint16(echo_context)
            datagram.add_uint8(0)
            datagram.add_uint32(100000001)
            self.handle_send_datagram(datagram)
        except:
            return self.handle_disconnect()

        self.network.account_manager.handle_create_avatar(self, self.__handle_create_avatar_resp,
            self._channel_alias, dna_string, index)

    def __handle_create_avatar_resp(self, avatar_id):
        pass

    def handle_set_avatar(self, di):
        try:
            avatar_id = di.get_uint32()
        except:
            return self.handle_disconnect()

        self.network.account_manager.handle_set_avatar(self, self.__handle_set_avatar_resp,
            avatar_id)

    def __handle_set_avatar_resp(self, avatar_id):
        pass

    def handle_avatar_details_resp(self, di):
        datagram = io.NetworkDatagram()
        datagram.add_uint16(types.CLIENT_GET_AVATAR_DETAILS_RESP)
        datagram.add_uint32(di.get_uint32())
        datagram.add_uint8(0)
        datagram.append_data(di.get_remaining_bytes())
        self.handle_send_datagram(datagram)

    def handle_set_wishname(self, di):
        try:
            avatar_id = di.get_uint32()
            wish_name = di.get_string()
        except:
            return self.handle_disconnect()

        datagram = io.NetworkDatagram()
        datagram.add_uint16(types.CLIENT_SET_WISHNAME_RESP)
        datagram.add_uint32(avatar_id)
        datagram.add_uint16(0)
        datagram.add_string('')
        datagram.add_string(wish_name)
        datagram.add_string('')
        self.handle_send_datagram(datagram)

    def handle_set_name_pattern(self, di):
        try:
            name_indices = []
            name_flags = []
            avatar_id = di.get_uint32()
            name_indices.append(di.get_uint16())
            name_flags.append(di.get_uint16())
            name_indices.append(di.get_uint16())
            name_flags.append(di.get_uint16())
            name_indices.append(di.get_uint16())
            name_flags.append(di.get_uint16())
            name_indices.append(di.get_uint16())
            name_flags.append(di.get_uint16())
        except:
            return self.handle_disconnect()

        #TODO: Actually parse and set the name pattern name.
        datagram = io.NetworkDatagram()
        datagram.add_uint16(types.CLIENT_SET_NAME_PATTERN_ANSWER)
        datagram.add_uint32(avatar_id)
        datagram.add_uint8(0)
        self.handle_send_datagram(datagram)

    def handle_set_shard(self, di):
        shard_id = di.get_uint32()

        datagram = io.NetworkDatagram()
        datagram.add_uint16(types.CLIENT_GET_STATE_RESP)
        self.handle_send_datagram(datagram)

    def handle_set_zone(self, di):
        try:
            zone_id = di.get_uint16()
        except:
            return self.handle_disconnect()

        datagram = io.NetworkDatagram()
        datagram.add_header(self._channel_alias, self.channel, types.STATESERVER_OBJECT_SET_ZONE)
        datagram.add_uint32(zone_id)
        self.network.handle_send_connection_datagram(datagram)

    def handle_set_zone_resp(self, di):
        datagram = io.NetworkDatagram()
        datagram.add_uint16(types.CLIENT_DONE_SET_ZONE_RESP)
        datagram.add_int16(di.get_uint32()) # why would the client identify a zone as an int16????
        self.handle_send_datagram(datagram)

    def handle_object_enter_location(self, has_other, di):
        do_id = di.get_uint64()
        parent_id = di.get_uint64()
        zone_id = di.get_uint32()
        dc_id = di.get_uint16()

        datagram = io.NetworkDatagram()

        if has_other:
            datagram.add_uint16(types.CLIENT_CREATE_OBJECT_REQUIRED_OTHER)
        else:
            datagram.add_uint16(types.CLIENT_CREATE_OBJECT_REQUIRED)

        datagram.add_uint16(dc_id)
        datagram.add_uint32(do_id)
        datagram.append_data(di.get_remaining_bytes())
        self.handle_send_datagram(datagram)

    def handle_object_update_field(self, di):
        do_id = di.get_uint32()
        field_id = di.get_uint16()

    def shutdown(self):
        if self.network.account_manager.has_fsm(self.channel):
            self.network.account_manager.stop_operation(self)

        if self.channel:
            self.network.channel_allocator.free(self.channel)

        io.NetworkHandler.shutdown(self)

class ClientAgent(io.NetworkListener, io.NetworkConnector):
    notify = directNotify.newCategory('ClientAgent')

    def __init__(self, dc_loader, address, port, connect_address, connect_port, channel):
        io.NetworkListener.__init__(self, address, port, Client)
        io.NetworkConnector.__init__(self, dc_loader, connect_address, connect_port, channel)

        self._channel_allocator = UniqueIdAllocator(config.GetInt('clientagent-min-channels', 1000000000),
            config.GetInt('clientagent-max-channels', 1009999999))

        self._server_version = config.GetString('clientagent-version', 'no-version')

        self._database_interface = io.NetworkDatabaseInterface(self)
        self._account_manager = ClientAccountManager(self)

    @property
    def channel_allocator(self):
        return self._channel_allocator

    @property
    def server_version(self):
        return self._server_version

    @property
    def database_interface(self):
        return self._database_interface

    @property
    def account_manager(self):
        return self._account_manager

    def setup(self):
        io.NetworkListener.setup(self)
        io.NetworkConnector.setup(self)

    def handle_datagram(self, channel, sender, message_type, di):
        handler = self.get_handler_from_channel(channel)

        if not handler:
            return

        handler.handle_internal_datagram(message_type, sender, di)

    def shutdown(self):
        io.NetworkListener.shutdown(self)
        io.NetworkConnector.shutdown(self)
