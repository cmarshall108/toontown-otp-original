"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, August 17th, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

from panda3d.core import QueuedConnectionManager, QueuedConnectionListener, QueuedConnectionReader, \
    ConnectionWriter, PointerToConnection, NetAddress, NetDatagram, DatagramIterator, Filename

from panda3d.direct import DCFile, DCPacker
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
                    field_name, dclass.getName()))

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

    def handle_datagram(self, message_type, di):
        if message_type == types.DBSERVER_CREATE_OBJECT_RESP:
            self.handle_create_object_resp(di)
        elif message_type == types.DBSERVER_OBJECT_GET_ALL_RESP:
            self.handle_query_object_resp(message_type, di)

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

class NetworkConnector(NetworkManager):
    notify = directNotify.newCategory('NetworkConnector')

    def __init__(self, dc_loader, address, port, channel, timeout=5000):
        NetworkManager.__init__(self)

        self.dc_loader = dc_loader
        self.__address = address
        self.__port = port
        self.channel = channel
        self.__timeout = timeout

        self.__manager = QueuedConnectionManager()
        self.__reader = QueuedConnectionReader(self.__manager, 0)
        self.__writer = ConnectionWriter(self.__manager, 0)

        self.__socket = None

        self.__read_task = None
        self.__disconnect_task = None

    def setup(self):
        if not self.__socket:
            self.__socket = self.__manager.open_TCP_client_connection(self.__address,
                self.__port, self.__timeout)

            if not self.__socket:
                raise NetworkError('Failed to connect TCP socket on address: <%s:%d>!' % (
                    self.__address, self.__port))

            self.__reader.add_connection(self.__socket)
            self.register_for_channel(self.channel)

        self.__read_task = task_mgr.add(self.__read_incoming, self.get_unique_name('read-incoming'))
        self.__disconnect_task = task_mgr.add(self.__listen_disconnect, self.get_unique_name('listen-disconnect'))

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

        di = DatagramIterator(datagram)

        if di.get_uint8() == 1:
            self.handle_datagram(di.get_uint64(), di.get_uint64(),
                di.get_uint16(), di)

    def handle_send_connection_datagram(self, datagram):
        """
        Sends a datagram to our connection
        """

        if not datagram.get_length():
            return

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

        self.unregister_for_channel(self.channel)
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
        self.network = network
        self.rendezvous = rendezvous
        self.address = address
        self.connection = connection
        self.channel = channel

        self.__data = []

        self.__update_task = None

    def setup(self):
        if not self.__update_task:
            self.__update_task = task_mgr.add(self.__update, self.get_unique_name('update-handler'))

        if self.channel:
            self.register_for_channel(self.channel)

    def register_for_channel(self, channel):
        """
        Registers our connections channel with the MessageDirector
        """

        datagram = NetworkDatagram()
        datagram.add_control_header(channel, types.CONTROL_SET_CHANNEL)
        self.network.handle_send_connection_datagram(datagram)

    def unregister_for_channel(self, channel):
        """
        Unregisters our connections channel from the MessageDirector
        """

        datagram = NetworkDatagram()
        datagram.add_control_header(channel, types.CONTROL_REMOVE_CHANNEL)
        self.network.handle_send_connection_datagram(datagram)

    def __update(self, task):
        """
        Pops a datagram from the queue and handles it
        """

        if not len(self.__data):
            return task.cont

        datagram = self.__data.pop()
        di = DatagramIterator(datagram)

        if not di.get_remaining_size():
            return task.cont

        self.handle_datagram(di)
        return task.cont

    def is_queued(self, datagram):
        """
        Returns true if the datagram is queued else False
        """

        return datagram in self.__data

    def queue(self, datagram):
        """
        Places a new datagram in the data queue
        """

        if self.is_queued(datagram) or not datagram.get_length():
            return

        self.__data.append(datagram)

    def dequeue(self, datagram):
        """
        Removes a datagram from the data queue
        """

        if not self.is_queued(datagram):
            return

        self.__data.remove(datagram)

    def handle_send_datagram(self, datagram):
        """
        Sends a datagram to our connection
        """

        self.network.handle_send_datagram(datagram, self.connection)

    def handle_datagram(self, di):
        """
        Handles a datagram that was pulled from the queue
        """

    def handle_disconnect(self):
        """
        Disconnects our client socket instance
        """

        self.network.handle_disconnect(self)

    def handle_disconnected(self):
        """
        Handles disconnection when the socket connection closes
        """

        if self.channel:
            self.unregister_for_channel(self.channel)

        self.network.handle_disconnected(self)

    def shutdown(self):
        if self.__update_task:
            task_mgr.remove(self.__update_task)

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

        self.__listen_task = task_mgr.add(self.__listen_incoming, self.get_unique_name('listen-incoming'))
        self.__read_task = task_mgr.add(self.__read_incoming, self.get_unique_name('read-incoming'))
        self.__disconnect_task = task_mgr.add(self.__listen_disconnect, self.get_unique_name('listen-disconnect'))

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

        return None

    def handle_send_datagram(self, datagram, connection):
        """
        Sends a datagram to a specific connection
        """

        if not datagram.get_length() or not self.__has_handler(connection):
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
