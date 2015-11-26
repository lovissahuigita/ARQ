Programming Assignment II - RxP Reliable Transfer Protocol
==========================================================
**CS 3251 Computer Networking I - Section B**

**Professors Russell Clark & Matt Sanders**

**November 26 2015**

Authors: Yoel Ivan (yivan3@gatech.edu) & Lovissa Winyoto (lwinyoto3@gatech.edu)

*Submitted File Description*
============================

**RxP** - Reliable Transfer Protocol
------------------------------------
- *__init__.py*:

- *Packet.py*: This class is a data holder for each packet instance. It contains information about the **source port**, **destination port**, **sequence number**, **acknowledgement number**, **checksum**, **window size**, and the **data**

- *Packeter.py*: The packeter class is a utility class that handles the packet object needs. This class handles calculating and validating **checksum**, converting data into packets ready to be sent, creating **YO! ACK CYA** packets, and converting objects to binary and binary to objects back and forth.

- *RxProtocol.py*: The RxProtocol class acts as a multiplexer between UDP and the RXP. This class holds the information of the actual sockets that each connection is connecting to. It has the information of which port is available, it can also gives an available port number. Everytime a socket needs a port number, RxProtocol has to know and keep track of the socket and port. The same rule applies to when a socket does not need a port anymore, it needs to report to RxProtocol as well. RxProtocol also handles socket sending and udp receiving.

- *rxpsocket.py*: The rxpsocket class knows the whole algorithm that needs to be done during the data transfer. This class is the 'controller' that calls the other classes' methods. It holds the state of the connection, sends and receive data through the RxProtocol, handles the handshake logic, handles duplicate and out of order packets, handles retransmisisons.

- *SendBuffer.py*: Send buffer works with the rxpsocket to hold the data to be sent by the rxpsocket to the peer. It handles sending ack number to the peer as well while sending packets to the peer.

- *RecvBuffer.py*: Receive buffer works with the rxpsocket to hold the data to be received by the rxpsocket from the peer. It handles notifying the received ack number from the peer as well while receiving from the peer.

- *RTOEstimator.py*: This class estimates the timeout time based on RTT. Everytime a packet is sent without any retransmission, the time needed until the ack packet arrives is computed and considered to be added to the statistic that estimates the Round Trip Time of a packet.

- *CongestionControl.py*: This file controls how fast should the socket send packets based on the window size of the peer. It implements Old Tahoe Congestion Control.

**FxA** - File Transfer Application
-----------------------------------

- *__init__.py*:

- *FxA-client.py*: The client module that tries to connect to the server in order to send and receive data with the server.

- *FxA-server.py*: The server module that listens to clients who need to connect in order to send and receive data with the server.

- *NetEmu.py*: Network Emulator that simulates the behavior of the network during data transaction

- *sock.py*: A wrapper class for the socket to be used by the client and server

- *util.py*: A utility class that contains a collection of shared function between classes.

FxA Server
----------

**Command-line**:

    ``> FxA-server X A P``

    + ``X``: the port number at which the FxA-server’s UDP socket should bind to (odd number)
    + ``A``: the IP address of NetEmu
    + ``P``: the UDP port number of NetEmu

**Command**:

+ Configure receiver maximum transfer window for the server:

    ``> window W``

    - ``W``: the maximum receiver’s window-size at the FxA-Server (in segments).

+ Shut down FxA-Server gracefully:

    ``> terminate``


FxA Client
----------

**Command-line**:

    ``> FxA-client X A P``

    + ``X``: the port number at which the FxA-client’s UDP socket should bind to (even number), this port number should be equal to the server’s port number minus 1.

    + ``A``: the IP address of NetEmu

    + ``P``: the UDP port number of NetEmu

**Command**:

+ FxA-client connects to the FxA-server (running at the same IP host):

    ``> connect``

+ FxA-client downloads file from the server:

    ``> get F``

    - ``F``: the file to be downloaded (if ``F`` exists in the same directory with the FxA-server program)

+ FxA-client uploads file to the server:

    ``> post F``

    - ``F``: the file to be uploaded (if ``F`` exists in the same directory with the FxA-client program)

+ Configure maximum receiver window size for the client:

    ``> window W``

    - ``W``: the maximum receiver’s window-size at the FxA-Client (in segments).

+ FxA-client terminates gracefully from the FxA-server:

    ``> disconnect``
