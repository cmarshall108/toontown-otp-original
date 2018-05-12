"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, August 17th, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import os

try:
    import ujson as json
except:
    import json

import yaml

from panda3d.core import UniqueIdAllocator
from panda3d.direct import DCPacker
from realtime import io, types
from direct.directnotify.DirectNotifyGlobal import directNotify

class DatabaseError(RuntimeError):
    """
    An database specific runtime error
    """

class DatabaseFile(object):

    def __init__(self, filename):
        self._filename = filename
        self._data = {}

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, filename):
        self._filename = filename

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        self._data = data

    def setup(self):
        if not os.path.exists(self._filename):
            self.save()

        self.load()

    def has_value(self, key):
        return key in self._data

    def set_value(self, key, value):
        self._data[key] = value
        self.save()

    def get_value(self, key):
        self.load()
        return self._data.get(key)

    def set_default_value(self, key, value):
        if self.has_value(key):
            return self.get_value(key)

        self.set_value(key, value)
        return value

    def close(self):
        self.save()

        self._filename = None
        self._data = None

    def shutdown(self):
        self.close()

class DatabaseJSONFile(DatabaseFile):

    def save(self):
        with open(self._filename, 'w') as io:
            json.dump(self._data, io, indent=2, sort_keys=True)
            io.close()

    def load(self):
        with open(self._filename, 'r') as io:
            self._data = json.load(io)
            io.close()

class DatabaseYAMLFile(DatabaseFile):

    def save(self):
        with open(self._filename, 'w') as io:
            yaml.dump(self._data, io, default_flow_style=False)
            io.close()

    def load(self):
        with open(self._filename, 'r') as io:
            self._data = yaml.load(io)
            io.close()

class DatabaseManager(object):

    def __init__(self, file_handler):
        self._files = {}
        self._file_handler = file_handler

        self._min_id = config.GetInt('database-min-channels', 100000000)
        self._max_id = config.GetInt('database-max-channels', 100999999)

        self._directory = config.GetString('database-directory', 'databases/json')
        self._extension = config.GetString('database-extension', '.json')

        if not os.path.exists(self._directory):
            os.makedirs(self._directory)

        self._tracker = None
        self._tracker_filename = config.GetString('database-tracker', 'next')

        self._allocator = None

    @property
    def files(self):
        return self._files

    @property
    def file_handler(self):
        return self._file_handler

    @file_handler.setter
    def file_handler(self, file_handler):
        self._file_handler = file_handler

    @property
    def min_id(self):
        return self._min_id

    @min_id.setter
    def min_id(self, min_id):
        self._min_id = min_id

    @property
    def max_id(self):
        return self._max_id

    @max_id.setter
    def max_id(self, max_id):
        self._max_id = max_id

    @property
    def directory(self):
        return self._directory

    @property
    def extension(self):
        return self._extension

    @property
    def tracker(self):
        return self._tracker

    @tracker.setter
    def tracker(self, tracker):
        self._tracker = tracker

    @property
    def tracker_filename(self):
        return self._tracker_filename

    @property
    def allocator(self):
        return self._allocator

    @allocator.setter
    def allocator(self, allocator):
        self._allocator = allocator

    def setup(self):
        self._tracker = self.open_file(self.get_filename(self._tracker_filename))
        self._min_id = self._tracker.set_default_value('next', self._min_id)
        self._allocator = UniqueIdAllocator(self._min_id, self._max_id)

    def has_file(self, filename):
        return filename in self._files

    def add_file(self, file):
        if self.has_file(file.filename):
            return

        file.setup()
        self._files[file.filename] = file

    def remove_file(self, file):
        if not self.has_file(file.filename):
            return

        del self._files[file.filename]
        file.shutdown()

    def get_file(self, filename):
        return self._files.get(filename)

    def get_filename(self, filename):
        return '%s%s' % (os.path.join(self._directory, str(filename)), self._extension)

    def open_file(self, filename):
        file = self._file_handler(filename)
        self.add_file(file)
        return file

    def close_file(self, file):
        if not isinstance(file, self._file_handler):
            raise DatabaseError('Cannot close file of invalid type: %r, expected: %r!' % (
                file, self._file_handler))

        self.remove_file(file)

    def shutdown(self):
        for file in self._files:
            self.remove_file(file)

class DatabaseJSONBackend(DatabaseManager):

    def __init__(self):
        DatabaseManager.__init__(self, DatabaseJSONFile)

class DatabaseYAMLBackend(DatabaseManager):

    def __init__(self):
        DatabaseManager.__init__(self, DatabaseYAMLFile)

class DatabaseServer(io.NetworkConnector):
    notify = directNotify.newCategory('DatabaseServer')

    def __init__(self, *args, **kwargs):
        io.NetworkConnector.__init__(self, *args, **kwargs)

        self._backend = DatabaseYAMLBackend()

    @property
    def backend(self):
        return self._backend

    @backend.setter
    def backend(self, backend):
        self._backend = backend

    def setup(self):
        self._backend.setup()

        io.NetworkConnector.setup(self)

    def handle_datagram(self, channel, sender, message_type, di):
        if message_type == types.DBSERVER_CREATE_OBJECT:
            self.handle_create_object(sender, di)
        elif message_type == types.DBSERVER_OBJECT_GET_ALL:
            self.handle_object_get_all(sender, di)

    def handle_create_object(self, sender, di):
        context = di.get_uint32()
        dc_id = di.get_uint16()
        field_count = di.get_uint16()
        dc_class = self.dc_loader.dclasses_by_number.get(dc_id)

        if not dc_class:
            self.notify.error('Failed to create object: %d context: %d, unknown dclass!' % (
                dc_id, context))

        do_id = self._backend.allocator.allocate()
        file_object = self._backend.open_file(self._backend.get_filename(do_id))

        file_object.set_value('dclass', dc_class.get_name())
        file_object.set_value('do_id', do_id)

        fields = {}
        field_packer = DCPacker()
        field_packer.set_unpack_data(di.get_remaining_bytes())

        for _ in xrange(field_count):
            field_id = field_packer.raw_unpack_uint16()
            field = dc_class.get_field_by_index(field_id)

            if not field:
                self.notify.error('Failed to unpack field: %d dclass: %s, invalid field!' % (
                    field_id, dclass.get_name()))

            field_packer.begin_unpack(field)
            field_args = field.unpack_args(field_packer)
            field_packer.end_unpack()

            if not field_args:
                self.notify.error('Failed to unpack field args for field: %d dclass: %s, invalid result!' % (
                    field.get_name(), dclass.get_name()))

            fields[field.get_name()] = field_args[0]

        file_object.set_value('fields', fields)

        self._backend.close_file(file_object)
        self._backend.tracker.set_value('next', do_id + 1)

        datagram = io.NetworkDatagram()
        datagram.add_header(sender, self.channel, types.DBSERVER_CREATE_OBJECT_RESP)
        datagram.add_uint32(context)
        datagram.add_uint32(do_id)
        self.handle_send_connection_datagram(datagram)

    def handle_object_get_all(self, sender, di):
        context = di.get_uint32()
        do_id = di.get_uint32()
        file_object = self._backend.open_file(self._backend.get_filename(do_id))

        if not file_object:
            self.notify.warning('Cannot get fields for object: %d context: %d, unknown object!' % (
                do_id, context))

            return

        dc_name = file_object.get_value('dclass')
        dc_class = self.dc_loader.dclasses_by_name.get(dc_name)

        if not dc_class:
            self.notify.warning('Failed to query object: %d context: %d, unknown dclass: %s!' % (
                do_id, context, dc_name))

            return

        fields = file_object.get_value('fields')

        if not fields:
            self.notify.warning('Failed to query object: %d context %d, invalid fields!' % (
                do_id, context))

            return

        datagram = io.NetworkDatagram()
        datagram.add_header(sender, self.channel, types.DBSERVER_OBJECT_GET_ALL_RESP)
        datagram.add_uint32(context)
        datagram.add_uint8(1)

        field_packer = DCPacker()
        field_count = 0
        for key, value in fields.items():
            field = dc_class.get_field_by_name(key)

            if not field:
                self.notify.warning('Failed to query object %d context: %d, unknown field: %s' % (
                    do_id, context, key))

                return

            field_packer.raw_pack_uint16(field.get_number())
            field_packer.begin_pack(field)
            field.pack_args(field_packer, (value,))
            field_packer.end_pack()
            field_count += 1

        self._backend.close_file(file_object)

        datagram.add_uint16(dc_class.get_number())
        datagram.add_uint16(field_count)
        datagram.append_data(field_packer.get_string())
        self.handle_send_connection_datagram(datagram)

    def shutdown(self):
        self._backend.shutdown()

        io.NetworkConnector.shutdown(self)
