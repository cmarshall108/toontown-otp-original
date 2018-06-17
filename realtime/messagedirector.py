"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, August 17th, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import time

from panda3d.core import Datagram
from realtime import io, types
from direct.directnotify.DirectNotifyGlobal import directNotify

class Participant(io.NetworkHandler):
    notify = directNotify.newCategory('Participant')

    def __init__(self, *args, **kwargs):
        io.NetworkHandler.__init__(self, *args, **kwargs)

    def handle_datagram(self, di):
        if di.get_uint8() == 1:
            self.handle_control_message(di)

    def handle_control_message(self, di):
        channel = di.get_uint64()

        if channel == types.CONTROL_MESSAGE:
            message_type = di.get_uint16()
            sender = di.get_uint64()

            if message_type == types.CONTROL_SET_CHANNEL:
                self.network.interface.add_channel(self, sender)
            elif message_type == types.CONTROL_REMOVE_CHANNEL:
                self.network.interface.remove_channel(self)
            elif message_type == types.CONTROL_ADD_POST_REMOVE:
                if not di.get_remaining_size():
                    return

                self.network.interface.add_post_remove(sender, io.NetworkDatagram(
                    Datagram(di.get_remaining_bytes())))
            elif message_type == types.CONTROL_CLEAR_POST_REMOVE:
                self.network.interface.remove_post_remove(self)
        else:
            self.network.message_interface.add_message(channel,
                di.get_uint64(), di)

    def handle_post_removes(self):
        for datagram in self.network.interface.get_post_removes(self):
            self.handle_datagram(io.NetworkDatagramIterator(datagram))

        self.network.interface.remove_post_remove(self)

    def handle_disconnected(self):
        self.handle_post_removes()
        self.network.interface.remove_channel(self)
        io.NetworkHandler.handle_disconnected(self)

class ParticipantInterface(object):
    notify = directNotify.newCategory('ParticipantInterface')

    def __init__(self):
        self._participants = {}
        self._post_removes = {}

    @property
    def participants(self):
        return self._participants

    @property
    def post_removes(self):
        return self._post_removes

    def has_channel(self, channel):
        return channel in self._participants

    def add_channel(self, participant, channel):
        if self.has_channel(channel):
            return

        self.notify.debug('Registered new channel: %d connection: %r' % (
            channel, participant.connection))

        participant.channel = channel
        self._participants[participant.channel] = participant

    def remove_channel(self, participant):
        if not self.has_channel(participant.channel):
            return

        self.notify.debug('Unregistered existing channel: %d connection: %r' % (
            participant.channel, participant.connection))

        del self._participants[participant.channel]
        participant.channel = None

    def get_participant(self, channel):
        return self._participants.get(channel)

    def has_post_remove(self, channel):
        return channel in self._post_removes

    def add_post_remove(self, channel, datagram):
        post_removes = self._post_removes.setdefault(channel, [])
        post_removes.append(datagram)

    def remove_post_remove(self, participant):
        if not self.has_post_remove(participant.channel):
            return

        del self._post_removes[participant.channel]

    def get_post_removes(self, participant):
        if not self.has_post_remove(participant.channel):
            return []

        return self._post_removes.pop(participant.channel)

class Message(object):

    def __init__(self, timestamp, channel, sender, message_type, datagram):
        self._timestamp = timestamp
        self._channel = channel
        self._sender = sender
        self._message_type = message_type
        self._datagram = datagram

    @property
    def timestamp(self):
        return self._timestamp

    @timestamp.setter
    def timestamp(self, timestamp):
        self._timestamp = timestamp

    @property
    def channel(self):
        return self._channel

    @channel.setter
    def channel(self, channel):
        self._channel = channel

    @property
    def sender(self):
        return self._sender

    @sender.setter
    def sender(self, sender):
        self._sender = sender

    @property
    def message_type(self):
        return self._message_type

    @message_type.setter
    def message_type(self, message_type):
        self._message_type = message_type

    @property
    def datagram(self):
        return self._datagram

    @datagram.setter
    def datagram(self, datagram):
        self._datagram = datagram

    def setup(self):
        pass

    def destroy(self):
        self._timestamp = None
        self._channel = None
        self._sender = None
        self._message_type = None
        self._datagram = None

class MessageInterface(object):

    def __init__(self, network):
        self._network = network

        self._messages = []
        self._message_timeout = config.GetFloat('messagedirector-message-timeout', 5.0)

        self.__send_task = None

    @property
    def network(self):
        return self._network

    @property
    def messages(self):
        return self._messages

    @property
    def message_timeout(self):
        return self._message_timeout

    @message_timeout.setter
    def message_timeout(self, message_timeout):
        self._message_timeout = message_timeout

    def get_timestamp(self):
        return round(time.time(), 2)

    def has_message(self, message):
        return message in self._messages

    def add_message(self, channel, sender, di):
        message = Message(self.get_timestamp(), channel, sender, di.get_uint16(),
            io.NetworkDatagram(Datagram(di.get_remaining_bytes())))

        message.setup()
        self._messages.append(message)

    def remove_message(self, message):
        if not self.has_message(message):
            return

        self._messages.remove(message)
        message.destroy()

    def setup(self):
        self.__send_task = task_mgr.add(self.__send_messages, self._network.get_unique_name(
            'send-messages'), taskChain=task_chain)

    def __send_messages(self, task):
        for message in self._messages:

            if self.get_timestamp() - message.timestamp > self._message_timeout:
                self.remove_message(message)
                continue

            if not self._network.interface.has_channel(message.channel):
                continue

            participant = self._network.interface.get_participant(message.channel)

            if participant:
                datagram = io.NetworkDatagram()
                datagram.add_header(message.channel, message.sender, message.message_type)
                datagram.append_data(message.datagram.get_message())
                participant.handle_send_datagram(datagram)

            self.remove_message(message)

        return task.cont

    def shutdown(self):
        if self.__send_task:
            task_mgr.remove(self.__send_task)

        self.__send_task = None

class MessageDirector(io.NetworkListener):
    notify = directNotify.newCategory('MessageDirector')

    def __init__(self, address, port):
        io.NetworkListener.__init__(self, address, port, Participant)

        self._interface = ParticipantInterface()
        self._message_interface = MessageInterface(self)

    @property
    def interface(self):
        return self._interface

    @property
    def message_interface(self):
        return self._message_interface

    def setup(self):
        self._message_interface.setup()

        io.NetworkListener.setup(self)

    def shutdown(self):
        self._message_interface.shutdown()

        io.NetworkListener.shutdown(self)
