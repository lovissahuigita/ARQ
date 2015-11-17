from socket import socket, AF_INET, SOCK_DGRAM

class Connection:


    def __init__(self):
        __netSocket = socket(AF_INET, SOCK_DGRAM)
        __netSocket.bind(address)
        __state =

    def getState(self):
    def initHandshake
    def initTearDown
    def getInitialSequenceNumber:    # this will be random
    def discoverMTU:                 # Look: PMTUD algorithm

