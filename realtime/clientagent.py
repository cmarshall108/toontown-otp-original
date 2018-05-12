"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, August 17th, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import time
import semidbm

from panda3d.core import UniqueIdAllocator, NetDatagram
from realtime import io, types
from direct.directnotify.DirectNotifyGlobal import directNotify
from direct.fsm.FSM import FSM

class ClientOperation(FSM):
    notify = directNotify.newCategory('ClientOperation')

    def __init__(self, client, play_token):
        FSM.__init__(self, self.__class__.__name__)

        self._client = client
        self._play_token = play_token

    def enterOff(self):
        pass

    def exitOff(self):
        pass

class ClientOperationManager(object):
    notify = directNotify.newCategory('ClientOperationManager')

    def __init__(self):
        self._channel2fsm = {}

    def has_fsm(self, channel):
        return channel in self._channel2fsm

    def add_fsm(self, channel, fsm):
        if self.has_fsm(channel):
            return None

        self._channel2fsm[channel] = fsm
        return fsm

    def remove_fsm(self, channel):
        if not self.has_fsm(channel):
            return None

        del self._channel2fsm[channel]

    def get_fsm(self, channel):
        return self._channel2fsm.get(channel)

class AccountFSM(ClientOperation):
    notify = directNotify.newCategory('AccountFSM')

    def enterLoad(self):
        pass

    def exitLoad(self):
        pass

class ClientAccountManager(ClientOperationManager):
    notify = directNotify.newCategory('ClientAccountManager')

    def login(self, client, play_token):
        fsm = self.add_fsm(client.channel, AccountFSM(client, play_token))

        if not fsm:
            self.notify.warning('Failed to add account operation for channel: %d with playtoken: %s!' % (
                client.channel, play_token))

            return

        fsm.request('Load')

    def abandon_login(self, client):
        fsm = self.get_fsm(client.channel)

        if not fsm:
            self.notify.warning('Failed to abandon account operation for channel: %d!' % (
                client.channel))

            return

        fsm.demand('Off')
        self.remove_fsm(client.channel)

class Client(io.NetworkHandler):
    notify = directNotify.newCategory('Client')

    def __init__(self, network, rendezvous, address, connection):
        io.NetworkHandler.__init__(self, network, rendezvous, address, connection)

    def setup(self):
        self.channel = self.network.channel_allocator.allocate()
        io.NetworkHandler.setup(self)

    def handle_send_disconnect(self, code, reason):
        datagram = NetDatagram()
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
        elif message_type == types.CLIENT_GET_SHARD_LIST:
            self.handle_get_shard_list()
        elif message_type == types.CLIENT_GET_AVATARS:
            self.handle_get_avatars()
        elif message_type == types.CLIENT_CREATE_AVATAR:
            self.handle_create_avatar(di)
        elif message_type == types.CLIENT_SET_AVATAR:
            self.handle_set_avatar(di)
        elif message_type == types.CLIENT_DISCONNECT:
            self.handle_disconnect()
        else:
            self.notify.warning('Unknown datagram recieved with message type: %d!' % (
                message_type))

    def handle_internal_datagram(self, message_type, sender, di):
        if message_type == types.STATESERVER_GET_SHARD_ALL_RESP:
            self.handle_get_shard_list_resp(di)
        else:
            self.notify.warning('Unknown internal datagram recieved with message type: %d!' % (
                message_type))

    def handle_login(self, di):
        play_token = di.get_string()
        server_version = di.get_string()
        hash_val = di.get_uint32()
        token_type = di.get_int32()

        if server_version != self.network.server_version:
            self.handle_send_disconnect(types.CLIENT_DISCONNECT_BAD_VERSION, "Invalid server version: %s, expected: %s!" % (
                server_version, self.network.server_version))

            return

        if token_type != types.CLIENT_LOGIN_2_PLAY_TOKEN:
            self.handle_send_disconnect(types.CLIENT_DISCONNECT_INVALID_PLAY_TOKEN_TYPE, "Invalid play token type: %d!" % (
                token_type))

            return

        self.network.account_manager.login(self, play_token)

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

    def handle_get_avatars(self):
        datagram = NetDatagram()
        datagram.add_uint16(types.CLIENT_GET_AVATARS_RESP)
        datagram.add_uint8(0)
        datagram.add_uint16(0)
        self.handle_send_datagram(datagram)

    def handle_create_avatar(self, di):
        echo_context = di.get_uint16()
        dna_string = di.get_string()
        index = di.get_uint8()

    def handle_set_avatar(self, di):
        avatar_id = di.get_uint32()

    def shutdown(self):
        if self.network.account_manager.has_fsm(self.channel):
            self.network.account_manager.abandon_login(self)

        self.network.channel_allocator.free(self.channel)
        io.NetworkHandler.shutdown(self)

class ClientAgent(io.NetworkListener, io.NetworkConnector):
    notify = directNotify.newCategory('ClientAgent')

    def __init__(self, dc_loader, address, port, connect_address, connect_port, channel):
        io.NetworkListener.__init__(self, address, port, Client)
        io.NetworkConnector.__init__(self, dc_loader, connect_address, connect_port, channel)

        self._channel_allocator = UniqueIdAllocator(config.GetInt('clientagent-min-channels', 1000000000),
            config.GetInt('clientagent-max-channels', 1009999999))

        self._server_version = config.GetString('server-version', 'no-version')

        self._account_manager = ClientAccountManager()

    @property
    def channel_allocator(self):
        return self._channel_allocator

    @property
    def server_version(self):
        return self._server_version

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
