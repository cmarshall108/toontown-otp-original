"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, August 17th, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import json
import os

from panda3d.core import NetDatagram, UniqueIdAllocator
from realtime import io, types
from direct.directnotify.DirectNotifyGlobal import directNotify

class JsonFile(object):
    notify = directNotify.newCategory('JsonFile')

    def __init__(self, filepath, mode='r+'):
        self.filepath = filepath
        self.mode = mode
        self.io = open(self.filepath, self.mode)
        self.__data = {}

    def setup(self):
        self.__load()

    def __getitem__(self, key):
        return self.__data.get(key)

    def __setitem__(self, key, value):
        self.__data[key] = value
        self.__save()

    def __save(self):
        self.io.write(str(json.dumps(self.__data, indent=2)))
        self.__load()

    def __load(self):
        try:
            self.__data = json.load(self.io)
        except:
            self.notify.debug('Failed to load json data from file: %s!' % self.filepath)

class JsonFileManager(object):
    notify = directNotify.newCategory('JsonFormatter')

    def __init__(self, backend):
        self.backend = backend

        self.__files = []

    def add_file(self, file):
        if file in self.__files:
            return

        self.__files.append(file)

    def remove_file(self, file):
        if file not in self.__files:
            return

        self.__files.remove(file)

    def setup(self, filepath):
        file = JsonFile(filepath, 'w+' if not os.path.exists(filepath) else 'r+')
        file.setup()
        self.add_file(file)
        return file

class DatabaseBackend(object):
    notify = directNotify.newCategory('DatabaseBackend')

    def __init__(self, min_id=0, max_id=0):
        self._min_id = min_id
        self._max_id = max_id

        self.allocator = UniqueIdAllocator(self._min_id, self._max_id)

class JsonDatabase(DatabaseBackend):
    notify = directNotify.newCategory('JsonDatabase')

    def __init__(self):
        DatabaseBackend.__init__(self, config.GetInt('database-min-channels', 100000000),
            config.GetInt('database-max-channels', 399999999))

        self.directory = config.GetString('database-directory', 'databases/json')
        self.extension = config.GetString('database-extension', '.json')

        self.tracker_filename = config.GetString('database-tracker', 'next')
        self.tracker = None

        self.file_manager = JsonFileManager(self)

    def get_filename(self, filename):
        return os.path.join(self.directory, str(filename)) + self.extension

    def setup(self):
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)

        if not os.path.exists(self.get_filename(self.tracker_filename)):
            self.create_tracker()
        else:
            self.read_tracker()

    def create_tracker(self):
        self.tracker = self.file_manager.setup(self.get_filename(self.tracker_filename))
        self.tracker['next'] = self._min_id

    def read_tracker(self):
        self.tracker = self.file_manager.setup(self.get_filename(self.tracker_filename))

class DatabaseServer(io.NetworkConnector):
    notify = directNotify.newCategory('DatabaseServer')

    def __init__(self, dc_loader, address, port, channel):
        io.NetworkConnector.__init__(self, dc_loader, address, port, channel)

        self.backend = JsonDatabase()

    def setup(self):
        io.NetworkConnector.setup(self)

        self.backend.setup()

    def handle_datagram(self, sender, message_type, di):
        pass
