# MessageDirector:
messagedirector-address 127.0.0.1
messagedirector-port 7100

# ClientAgent:
clientagent-address 127.0.0.1
clientagent-port 6667
clientagent-channel 1000
clientagent-max-channels 1000001000
clientagent-min-channels 1000000000
clientagent-dbm-filename databases/database.dbm
clientagent-dbm-mode c
clientagent-version sv1.0.6.9

# StateServer:
stateserver-channel 1001

# Database:
database-channel 1002
database-directory databases/json
database-extension .json
database-max-channels 100999999
database-min-channels 100000000
