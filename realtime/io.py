"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, August 17th, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import Queue

from panda3d.core import QueuedConnectionManager, QueuedConnectionListener, QueuedConnectionReader, \
    ConnectionWriter, PointerToConnection, NetAddress, NetDatagram, DatagramIterator, Filename

from panda3d.direct import DCFile, DCPacker
from direct.distributed.PyDatagramIterator import PyDatagramIterator
from realtime import types
from direct.directnotify.DirectNotifyGlobal import directNotify

class NetworkError(RuntimeError):
    """
    A network specific runtime error
    """

class NetworkDatagram(NetDatagram):
    """
    A class that inherits from panda's C++ NetDatagram buffer.
    This class adds useful methods and functions for talking
    to the OTP's internal cluster participants...
    """

    def add_header(self, channel, sender, message_type):
        self.add_uint8(1)
        self.add_uint64(channel)
        self.add_uint64(sender)
        self.add_uint16(message_type)

    def add_control_header(self, channel, message_type):
        self.add_uint8(1)
        self.add_uint64(types.CONTROL_MESSAGE)
        self.add_uint16(message_type)
        self.add_uint64(channel)

class NetworkDatagramIterator(PyDatagramIterator):
    """
    A class that inherits from panda's C++ DatagramIterator buffer.
    This class adds useful methods and functions for talking
    to the OTP's internal cluster participants...
    """

class NetworkDatabaseInterface(object):
    notify = directNotify.newCategory('NetworkDatabaseInterface')

    def __init__(self, network):
        self._network = network

        self._context = 0

        self._callbacks = {}
        self._dclasses = {}

    def get_context(self):
        self._context = (self._context + 1) & 0xFFFFFFFF
        return self._context

    def create_object(self, channel_id, database_id, dclass, fields={}, callback=None):
        """
        Create an object in the specified database.
        database_id specifies the control channel of the target database.
        dclass specifies the class of the object to be created.
        fields is a dict with any fields that should be stored in the object on creation.
        callback will be called with callback(do_id) if specified. On failure, do_id is 0.
        """

        # Save the callback:
        ctx = self.get_context()
        self._callbacks[ctx] = callback

        # Pack up/count valid fields.
        field_packer = DCPacker()
        field_count = 0
        for k,v in fields.items():
            field = dclass.get_field_by_name(k)
            if not field:
                self.notify.error('Creation request for %s object contains an invalid field named %s' % (
                    dclass.get_name(), k))

            field_packer.raw_pack_uint16(field.get_number())
            field_packer.begin_pack(field)
            field.pack_args(field_packer, v)
            field_packer.end_pack()
            field_count += 1

        # Now generate and send the datagram:
        dg = NetworkDatagram()
        dg.add_header(database_id, channel_id, types.DBSERVER_CREATE_OBJECT)
        dg.add_uint32(ctx)
        dg.add_uint16(dclass.get_number())
        dg.add_uint16(field_count)
        dg.append_data(field_packer.get_string())
        self._network.handle_send_connection_datagram(dg)

    def handle_create_object_resp(self, di):
        ctx = di.get_uint32()
        do_id = di.get_uint32()

        if ctx not in self._callbacks:
            self.notify.warning('Received unexpected DBSERVER_CREATE_OBJECT_RESP (ctx %d, do_id %d)' % (
                ctx, do_id))

            return

        if self._callbacks[ctx]:
            self._callbacks[ctx](do_id)

        del self._callbacks[ctx]

    def query_object(self, channel_id, database_id, do_id, callback, dclass=None, field_names=()):
        """
        Query object `do_id` out of the database.
        On success, the callback will be invoked as callback(dclass, fields)
        where dclass is a DCClass instance and fields is a dict.
        On failure, the callback will be invoked as callback(None, None).
        """

        # Save the callback:
        ctx = self.get_context()
        self._callbacks[ctx] = callback
        self._dclasses[ctx] = dclass

        # Generate and send the datagram:
        dg = NetworkDatagram()

        if not field_names:
            dg.add_header(database_id, channel_id, types.DBSERVER_OBJECT_GET_ALL)
        else:
            # We need a dclass in order to convert the field names into field IDs:
            assert dclass is not None

            if len(field_names) > 1:
                dg.add_header(database_id, channel_id, types.DBSERVER_OBJECT_GET_FIELDS)
            else:
                dg.add_header(database_id, channel_id, types.DBSERVER_OBJECT_GET_FIELD)

        dg.add_uint32(ctx)
        dg.add_uint32(do_id)
        if len(field_names) > 1:
            dg.add_uint16(len(field_names))

        for field_name in field_names:
            field = dclass.get_field_by_name(field_name)
            if field is None:
                self.notify.error('Bad field named %s in query for %s object' % (
                    field_name, dclass.get_name()))

            dg.add_uint16(field.get_number())

        self._network.handle_send_connection_datagram(dg)

    def handle_query_object_resp(self, message_type, di):
        ctx = di.get_uint32()
        success = di.get_uint8()

        if ctx not in self._callbacks:
            self.notify.warning('Received unexpected %s (ctx %d)' % (
                MsgId2Names[message_type], ctx))

            return

        try:
            if not success:
                if self._callbacks[ctx]:
                    self._callbacks[ctx](None, None)

                return

            if message_type == types.DBSERVER_OBJECT_GET_ALL_RESP:
                dclass_id = di.get_uint16()
                dclass = self._network.dc_loader.dclasses_by_number.get(dclass_id)
            else:
                dclass = self._dclasses[ctx]

            if not dclass:
                self.notify.error('Received bad dclass %d in DBSERVER_OBJECT_GET_ALL_RESP' % (
                    dclass_id))

            if message_type == types.DBSERVER_OBJECT_GET_FIELD_RESP:
                field_count = 1
            else:
                field_count = di.get_uint16()

            field_packer = DCPacker()
            field_packer.set_unpack_data(di.get_remaining_bytes())
            fields = {}
            for x in xrange(field_count):
                field_id = field_packer.raw_unpack_uint16()
                field = dclass.get_field_by_index(field_id)

                if not field:
                    self.notify.error('Received bad field %d in query for %s object' % (
                        field_id, dclass.get_name()))

                field_packer.begin_unpack(field)
                fields[field.get_name()] = field.unpack_args(field_packer)
                field_packer.end_unpack()

            if self._callbacks[ctx]:
                self._callbacks[ctx](dclass, fields)

        finally:
            del self._callbacks[ctx]
            del self._dclasses[ctx]

    def update_object(self, channel_id, database_id, do_id, dclass, new_fields, old_fields=None, callback=None):
        """
        Update field(s) on an object, optionally with the requirement that the
        fields must match some old value.
        database_id and do_id represent the database control channel and object ID
        for the update request.
        new_fields is to be a dict of fieldname->value, representing the fields
        to add/change on the database object.
        old_fields, if specified, is a similarly-formatted dict that contains the
        expected older values. If the values do not match, the database will
        refuse to process the update. This is useful for guarding against race
        conditions.
        On success, the callback is called as callback(None).
        On failure, the callback is called as callback(dict), where dict contains
        the current object values. This is so that the updater can try again,
        basing its updates off of the new values.
        """

        # Ensure that the keys in new_fields and old_fields are the same if
        # old_fields is given...
        if old_fields is not None:
            if set(new_fields.keys()) != set(old_fields.keys()):
                self.notify.error('new_fields and old_fields must contain the same keys!')
                return

        field_packer = DCPacker()
        field_count = 0
        for k,v in new_fields.items():
            field = dclass.get_field_by_name(k)
            if not field:
                self.notify.error('Update for %s(%d) object contains invalid field named %s' % (
                    dclass.get_name(), do_id, k))

            field_packer.raw_pack_uint16(field.get_number())

            if old_fields is not None:
                # Pack the old values:
                field_packer.begin_pack(field)
                field.pack_args(field_packer, old_fields[k])
                field_packer.end()

            field_packer.begin_pack(field)
            field.pack_args(field_packer, v)
            field_packer.end_pack()
            field_count += 1

        # Generate and send the datagram:
        dg = NetworkDatagram()
        if old_fields is not None:
            ctx = self.get_context()
            self._callbacks[ctx] = callback
            if field_count == 1:
                dg.add_header(database_id, channel_id, types.DBSERVER_OBJECT_SET_FIELD_IF_EQUALS)
            else:
                dg.add_header(database_id, channel_id, types.DBSERVER_OBJECT_SET_FIELDS_IF_EQUALS)

            dg.add_uint32(ctx)
        else:
            if field_count == 1:
                dg.add_header(database_id, channel_id, types.DBSERVER_OBJECT_SET_FIELD)
            else:
                dg.add_header(database_id, channel_id, types.DBSERVER_OBJECT_SET_FIELDS)

        dg.add_uint32(do_id)
        if field_count != 1:
            dg.add_uint16(field_count)

        dg.append_data(field_packer.getString())
        self._network.handle_send_connection_datagram(dg)

        if old_fields is None and callback is not None:
            # Why oh why did they ask for a callback if there's no old_fields?
            # Oh well, better honor their request:
            callback(None)

    def handle_update_object_resp(self, di, multi):
        ctx = di.get_uint32()
        success = di.get_uint8()

        if ctx not in self._callbacks:
            self.notify.warning('Received unexpected DBSERVER_OBJECT_SET_FIELD(S)_IF_EQUALS_RESP (ctx %d)' % (
                ctx))

            return

        try:
            if success:
                if self._callbacks[ctx]:
                    self._callbacks[ctx](None)

                return

            if not di.get_remaining_size():
                # We failed due to other reasons.
                if self._callbacks[ctx]:
                    return self._callbacks[ctx]({})

            if multi:
                field_count = di.get_uint16()
            else:
                field_count = 1

            field_packer = DCPacker()
            field_packer.set_unpack_data(di.get_remaining_bytes())
            fields = {}
            for x in xrange(field_count):
                fieldId = field_packer.raw_pack_uint16()
                field = self._network.dc_loader.dc_file.get_field_by_index(fieldId)

                if not field:
                    self.notify.error('Received bad field %d in update failure response message' % (
                        fieldId))

                field_packer.begin_unpack(field)
                fields[field.get_name()] = field.unpack_args(field_packer)
                field_packer.end_unpack()

            if self._callbacks[ctx]:
                self._callbacks[ctx](fields)

        finally:
            del self._callbacks[ctx]

    def handle_datagram(self, message_type, di):
        if message_type == types.DBSERVER_CREATE_OBJECT_RESP:
            self.handle_create_object_resp(di)
        elif message_type in (types.DBSERVER_OBJECT_GET_ALL_RESP,
                              types.DBSERVER_OBJECT_GET_FIELDS_RESP,
                              types.DBSERVER_OBJECT_GET_FIELD_RESP):
            self.handle_query_object_resp(message_type, di)
        elif message_type == types.DBSERVER_OBJECT_SET_FIELD_IF_EQUALS_RESP:
            self.handle_update_object_resp(di, False)
        elif message_type == types.DBSERVER_OBJECT_SET_FIELDS_IF_EQUALS_RESP:
            self.handle_update_object_resp(di, True)

class NetworkDCLoader(object):
    notify = directNotify.newCategory('NetworkDCLoader')

    def __init__(self):
        self._dc_file = DCFile()
        self._dc_suffix = ""

        self._dclasses_by_name = {}
        self._dclasses_by_number = {}

        self._hash_value = 0

    @property
    def dc_file(self):
        return self._dc_file

    @property
    def dc_suffix(self):
        return self._dc_suffix

    @property
    def dclasses_by_name(self):
        return self._dclasses_by_name

    @property
    def dclasses_by_number(self):
        return self._dclasses_by_number

    @property
    def hash_value(self):
        return self._hash_value

    def read_dc_files(self, dc_file_names=None):
        dc_imports = {}
        if dc_file_names == None:
            read_result = self._dc_file.read_all()
            if not read_result:
                self.notify.error("Could not read dc file.")
        else:
            for dc_fileName in dc_file_names:
                pathname = Filename(dc_fileName)
                read_result = self._dc_file.read(pathname)
                if not read_result:
                    self.notify.error("Could not read dc file: %s" % (
                        pathname))

        self._hash_value = self._dc_file.get_hash()

        # Now get the class definition for the classes named in the DC
        # file.
        for i in range(self._dc_file.get_num_classes()):
            dclass = self._dc_file.get_class(i)
            number = dclass.get_number()
            class_name = dclass.get_name() + self._dc_suffix

            # Does the class have a definition defined in the newly
            # imported namespace?
            class_def = dc_imports.get(class_name)

            # Also try it without the dc_suffix.
            if class_def == None:
                class_name = dclass.get_name()
                class_def = dc_imports.get(class_name)

            if class_def == None:
                self.notify.debug("No class definition for %s." % (
                    class_name))
            else:
                if inspect.ismodule(class_def):
                    if not hasattr(class_def, class_name):
                        self.notify.error("Module %s does not define class %s." % (
                            class_name, class_name))

                    class_def = getattr(class_def, class_name)

                if not inspect.isclass(class_def):
                    self.notify.error("Symbol %s is not a class name." % (
                        class_name))
                else:
                    dclass.set_class_def(class_def)

            self._dclasses_by_name[class_name] = dclass
            if number >= 0:
                self._dclasses_by_number[number] = dclass

class NetworkManager(object):
    notify = directNotify.newCategory('NetworkManager')

    def get_unique_name(self, name):
        return '%s-%s-%s' % (self.__class__.__name__, name, id(self))

    def get_puppet_connection_channel(self, doId):
        return doId + (1001 << 32)

    def get_account_connection_channel(self, doId):
        return doId + (1003 << 32)

    def get_account_id_from_channel_code(self, channel):
        return channel >> 32

    def get_avatar_id_from_connection_channel(self, channel):
        return channel & 0xffffffff

class NetworkConnector(NetworkManager):
    notify = directNotify.newCategory('NetworkConnector')

    def __init__(self, dc_loader, address, port, channel, timeout=5000):
        NetworkManager.__init__(self)

        self._dc_loader = dc_loader
        self.__address = address
        self.__port = port
        self._channel = channel
        self.__timeout = timeout

        self.__manager = QueuedConnectionManager()
        self.__reader = QueuedConnectionReader(self.__manager, 0)
        self.__writer = ConnectionWriter(self.__manager, 0)

        self.__socket = None

        self.__read_task = None
        self.__disconnect_task = None

    @property
    def dc_loader(self):
        return self._dc_loader

    @property
    def channel(self):
        return self._channel

    @channel.setter
    def channel(self, channel):
        self._channel = channel

    def setup(self):
        if not self.__socket:
            self.__socket = self.__manager.open_TCP_client_connection(self.__address,
                self.__port, self.__timeout)

            if not self.__socket:
                raise NetworkError('Failed to connect TCP socket on address: <%s:%d>!' % (
                    self.__address, self.__port))

            self.__reader.add_connection(self.__socket)
            self.register_for_channel(self._channel)

        self.__read_task = task_mgr.add(self.__read_incoming, self.get_unique_name(
            'read-incoming'), taskChain=task_chain)

        self.__disconnect_task = task_mgr.add(self.__listen_disconnect, self.get_unique_name(
            'listen-disconnect'), taskChain=task_chain)

    def register_for_channel(self, channel):
        """
        Registers our connections channel with the MessageDirector
        """

        datagram = NetworkDatagram()
        datagram.add_control_header(channel, types.CONTROL_SET_CHANNEL)
        self.handle_send_connection_datagram(datagram)

    def unregister_for_channel(self, channel):
        """
        Unregisters our connections channel from the MessageDirector
        """

        datagram = NetworkDatagram()
        datagram.add_control_header(channel, types.CONTROL_REMOVE_CHANNEL)
        self.handle_send_connection_datagram(datagram)

    def __read_incoming(self, task):
        """
        Polls for incoming data
        """

        if self.__reader.data_available():
            datagram = NetworkDatagram()

            if self.__reader.get_data(datagram):
                self.__handle_data(datagram)

        return task.cont

    def __listen_disconnect(self, task):
        """
        Watches our connected socket object and determines if the stream has ended..
        """

        if not self.__reader.is_connection_ok(self.__socket):
            self.handle_disconnected()
            return task.done

        return task.cont

    def __handle_data(self, datagram):
        """
        Handles incoming data from the connector
        """

        if not datagram.get_length():
            return

        di = NetworkDatagramIterator(datagram)
        code = di.get_uint8()

        self.handle_datagram(di.get_uint64(), di.get_uint64(), di.get_uint16(), di)

    def handle_send_connection_datagram(self, datagram):
        """
        Sends a datagram to our connection
        """

        self.__writer.send(datagram, self.__socket)

    def handle_datagram(self, channel, sender, message_type, di):
        """
        Handles a datagram that was pulled from the queue
        """

    def handle_disconnect(self):
        """
        Disconnects our client socket instance
        """

        self.__manager.close_connection(self.__socket)

    def handle_disconnected(self):
        """
        Handles disconnection when the socket connection closes
        """

        self.unregister_for_channel(self._channel)
        self.__reader.remove_connection(self.__socket)

    def shutdown(self):
        if self.__read_task:
            task_mgr.remove(self.__read_task)

        if self.__disconnect_task:
            task_mgr.remove(self.__disconnect_task)

        self.__read_task = None
        self.__disconnect_task = None

class NetworkHandler(NetworkManager):
    notify = directNotify.newCategory('NetworkHandler')

    def __init__(self, network, rendezvous, address, connection, channel=None):
        self._network = network
        self._rendezvous = rendezvous
        self._address = address
        self._connection = connection
        self._channel = channel
        self._allocated_channel = channel

        self._readable = Queue.Queue()
        self.__update_task = None

    @property
    def network(self):
        return self._network

    @property
    def rendezvous(self):
        return self._rendezvous

    @property
    def address(self):
        return self._address

    @property
    def connection(self):
        return self._connection

    @property
    def channel(self):
        return self._channel

    @channel.setter
    def channel(self, channel):
        if not self._channel:
            self._allocated_channel = channel

        self._channel = channel

    @property
    def allocated_channel(self):
        return self._allocated_channel

    @allocated_channel.setter
    def allocated_channel(self, allocated_channel):
        self._allocated_channel = allocated_channel

    def setup(self):
        if not self.__update_task:
            self.__update_task = task_mgr.add(self.__update, self.get_unique_name(
                'update-handler'), taskChain=task_chain)

        if self._channel:
            self.register_for_channel(self._channel)

    def register_for_channel(self, channel):
        """
        Registers our connections channel with the MessageDirector
        """

        datagram = NetworkDatagram()
        datagram.add_control_header(channel, types.CONTROL_SET_CHANNEL)
        self._network.handle_send_connection_datagram(datagram)

    def unregister_for_channel(self, channel):
        """
        Unregisters our connections channel from the MessageDirector
        """

        datagram = NetworkDatagram()
        datagram.add_control_header(channel, types.CONTROL_REMOVE_CHANNEL)
        self._network.handle_send_connection_datagram(datagram)

    def handle_set_channel_id(self, channel):
        if channel != self._channel:
            self.unregister_for_channel(self._channel)

        self._channel = channel
        self.register_for_channel(channel)

    def __update(self, task):
        """
        Pops a datagram from the queue and handles it
        """

        if self._readable.empty():
            return task.cont

        datagram = self._readable.get_nowait()
        di = NetworkDatagramIterator(datagram)

        if not di.get_remaining_size():
            return task.cont

        self.handle_datagram(di)
        return task.cont

    def queue(self, datagram):
        """
        Places a new datagram in the data queue
        """

        self._readable.put_nowait(datagram)

    def handle_send_datagram(self, datagram):
        """
        Sends a datagram to our connection
        """

        self._network.handle_send_datagram(datagram, self._connection)

    def handle_datagram(self, di):
        """
        Handles a datagram that was pulled from the queue
        """

    def handle_disconnect(self):
        """
        Disconnects our client socket instance
        """

        self._network.handle_disconnect(self)

    def handle_disconnected(self):
        """
        Handles disconnection when the socket connection closes
        """

        if self._channel:
            self.unregister_for_channel(self._channel)

        self._network.handle_disconnected(self)

    def shutdown(self):
        if self.__update_task:
            task_mgr.remove(self.__update_task)

        self.__update_task = None

class NetworkListener(NetworkManager):
    notify = directNotify.newCategory('NetworkListener')

    def __init__(self, address, port, handler, backlog=10000):
        NetworkManager.__init__(self)

        self.__address = address
        self.__port = port
        self.__handler = handler
        self.__backlog = backlog

        self.__manager = QueuedConnectionManager()
        self.__listener = QueuedConnectionListener(self.__manager, 0)
        self.__reader = QueuedConnectionReader(self.__manager, 0)
        self.__writer = ConnectionWriter(self.__manager, 0)

        self.__socket = None
        self.__handlers = {}

        self.__listen_task = None
        self.__read_task = None
        self.__disconnect_task = None

    def setup(self):
        if not self.__socket:
            self.__socket = self.__manager.open_TCP_server_rendezvous(self.__address,
                self.__port, self.__backlog)

            if not self.__socket:
                raise NetworkError('Failed to bind TCP socket on address: <%s:%d>!' % (
                    self.__address, self.__port))

            self.__listener.add_connection(self.__socket)

        self.__listen_task = task_mgr.add(self.__listen_incoming, self.get_unique_name(
            'listen-incoming'), taskChain=task_chain)

        self.__read_task = task_mgr.add(self.__read_incoming, self.get_unique_name(
            'read-incoming'), taskChain=task_chain)

        self.__disconnect_task = task_mgr.add(self.__listen_disconnect, self.get_unique_name(
            'listen-disconnect'), taskChain=task_chain)

    def __listen_incoming(self, task):
        """
        Polls for incoming connections
        """

        if self.__listener.new_connection_available():
            rendezvous = PointerToConnection()
            address = NetAddress()
            connection = PointerToConnection()

            if self.__listener.get_new_connection(rendezvous, address, connection):
                self.__handle_connection(rendezvous, address, connection.p())

        return task.cont

    def __read_incoming(self, task):
        """
        Polls for incoming data
        """

        if self.__reader.data_available():
            datagram = NetworkDatagram()

            if self.__reader.get_data(datagram):
                self.__handle_data(datagram, datagram.get_connection())

        return task.cont

    def __listen_disconnect(self, task):
        """
        Watches all connected socket objects and determines if the stream has ended...
        """

        for handler in self.__handlers.values():
            if not self.__reader.is_connection_ok(handler.connection):
                handler.handle_disconnected()

        return task.cont

    def __has_handler(self, connection):
        """
        Returns True if the handler is queued else False
        """

        return connection in self.__handlers

    def __add_handler(self, handler):
        """
        Adds a handler to the handlers dictionary
        """

        if self.__has_handler(handler.connection):
            return

        handler.setup()
        self.__handlers[handler.connection] = handler
        self.__reader.add_connection(handler.connection)

    def __remove_handler(self, handler):
        """
        Removes a handler from the handlers dictionary
        """

        if not self.__has_handler(handler.connection):
            return

        handler.shutdown()
        self.__reader.remove_connection(handler.connection)
        del self.__handlers[handler.connection]

    def __handle_connection(self, rendezvous, address, connection):
        """
        Handles an incoming connection from the connection listener
        """

        handler = self.__handler(self, rendezvous, address, connection)
        self.__add_handler(handler)

    def __handle_data(self, datagram, connection):
        """
        Handles new data incoming from the connection reader
        """

        if not self.__has_handler(connection):
            return

        self.__handlers[connection].queue(datagram)

    def get_handler_from_channel(self, channel):
        """
        Returns a handler instance if one is associated with that channel
        """

        for connection, handler in self.__handlers.items():

            if handler.channel == channel:
                return handler

            if self.get_account_connection_channel(self.get_account_id_from_channel_code(
                self.channel)) == channel:

                return handler

            if self.get_puppet_connection_channel(self.get_avatar_id_from_connection_channel(
                self.channel)) == channel:

                return handler

        return None

    def handle_send_datagram(self, datagram, connection):
        """
        Sends a datagram to a specific connection
        """

        if not self.__has_handler(connection):
            return

        self.__writer.send(datagram, connection)

    def handle_disconnect(self, handler):
        """
        Disconnects the handlers client socket instance
        """

        self.__manager.close_connection(handler.connection)

    def handle_disconnected(self, handler):
        """
        Handles disconnection of a client socket instance
        """

        self.__remove_handler(handler)

    def shutdown(self):
        if self.__listen_task:
            task_mgr.remove(self.__listen_task)

        if self.__read_task:
            task_mgr.remove(self.__read_task)

        if self.__disconnect_task:
            task_mgr.remove(self.__disconnect_task)

        self.__listen_task = None
        self.__read_task = None
        self.__disconnect_task = None

        self.__listener.remove_connection(self.__socket)
