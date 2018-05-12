"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, August 17th, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import __builtin__
import os

from panda3d.core import loadPrcFile

if os.path.exists('config/general.prc'):
    loadPrcFile('config/general.prc')

from panda3d.direct import get_config_showbase
from direct.task.TaskManagerGlobal import taskMgr as task_mgr
from direct.directnotify.DirectNotifyGlobal import directNotify

__builtin__.config = get_config_showbase()
__builtin__.task_mgr = task_mgr

from realtime import io, types, clientagent, messagedirector, \
    stateserver, database

notify = directNotify.newCategory('Main')
notify.setInfo(True)

def setup_component(cls, *args, **kwargs):
    notify.info('Starting component: %s...' % (
        cls.__name__))

    component = cls(*args, **kwargs)
    component.setup()

def shutdown_component(cls):
    notify.info('Stopping component: %s...' % (
        cls.__name__))

    cls.shutdown()

def main():
    dc_loader = io.NetworkDCLoader()
    dc_loader.read_dc_files(['config/dclass/toon.dc'])

    message_director_address = config.GetString('messagedirector-address', '0.0.0.0')
    message_director_port = config.GetInt('messagedirector-port', 7100)

    client_agent_address = config.GetString('clientagent-address', '0.0.0.0')
    client_agent_port = config.GetInt('clientagent-port', 6667)

    client_agent_channel = config.GetInt('clientagent-channel', types.CLIENTAGENT_CHANNEL)
    state_server_channel = config.GetInt('stateserver-channel', types.STATESERVER_CHANNEL)
    database_channel = config.GetInt('database-channel', types.DATABASE_CHANNEL)

    message_director = setup_component(messagedirector.MessageDirector, message_director_address,
        message_director_port)

    client_agent = setup_component(clientagent.ClientAgent, dc_loader, client_agent_address,
        client_agent_port, message_director_address, message_director_port,
        client_agent_channel)

    state_server = setup_component(stateserver.StateServer, dc_loader, message_director_address,
        message_director_port, state_server_channel)

    database_server = setup_component(database.DatabaseServer, dc_loader, message_director_address,
        message_director_port, database_channel)

if __name__ == '__main__':
    main()
    task_mgr.run()
