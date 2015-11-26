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

*Compiling and Running Client-Server*
=====================================

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

*Updated Protocol*
==================

**Four-Way Handshake**

- The client sends a YO! segment to the server to initiate contact

- The server responds by sending a YO! segment back to the client, containing a sequence number that will be used during the connection

- The client responds to the server by sending an ACK segment to the server with an acknowledgment number that follows the sequence number sent before. In this stage, the server’s connection is open to the client, and the server is now able to send data to the client

- Finally, the server sends an ACK segment to the client, indicating that the client’s connection is open and that the client is now able to send data to the server. 

**Three-Way Closing Handshake**

- A host send a CYA segment to initiate closing sequence whenever that host have no longer data to send.

- The closing sequence responder then will still continue sending data if any, and the closing sequence initiator will still have to receive the data.

- Once the closing sequence responder has no more data to send, the responder will send a CYA+ACK segment.

- The initiator then send an ACK packet to the the responder. Responder connection is now terminated, any resources allocated for that connection is now freed.

- The initiator will then wait for a period of time, to make sure the ACK sent is received by the responder.
Once the wait period ends, the initiator connection is then terminated, any resources allocated for that connection is now freed.

**Four-Way Closing Handshake**

The four-way closing handshake behaves similarly to the three-way closing handshake procedure. The only difference presence is when the responder receives a CYA segment, it sends back an ACK segment back to the initiator instead of sending back CYA+ACK to the initiator. The responder will then send a separate CYA segment when it’s done sending segments.

RxP protocol closing handshake supports both three-way or four-way closing handshake depending on the implementation of the socket.

**Multiplexing**

The idea of multiplexing in the RxP algorithm is to tell which socket is receiving which packet. Since RxP is implemented on top of an unreliable protocol, multiplexing is implemented by keeping track each connection’s states throughout all packet transactions. This requires the receiver to store information of the current open packet transactions. RxP socket keeps track of the states of each connection instead of the multiplexor underneath it. The peer does not know the socket in the protocol that is assigned for them to communicate with. Different peers will communicate with the same listener IP address and port. The RxP protocol is the layer below the RxP socket and it is implemented to keep track of the peer’s IP address and port number. From that information, it multiplexes to the assigned socket for each peer to communicate.

**Cumulative ACK**

ACK bit indicate cumulative ACK, Receive Window will contain the number of byte receiver capable to receive. Upon receiving cumulative ACK, sender should send remaining unsent segments starting with sequence number=ACK  number until sequence number=ACK  number+receive window.

**Computing checksum**

- Set all header field with its intended value and put the data (if any) except for the checksum field.

- Set the checksum to 0

- Read the segment 16-bit at a time and compute the sum of it, ignore any overflow bit

- Put the negation of the total sum into the checksum field.

**Verifying segment integrity**

- Store the checksum field in some temporary variable

- Set the checksum field to 0

- Read the packet 16-bit at a time and keep track the sum, ignore any overflow bit

- Sum the result with the stored checksum

- if the result is all 1’s, the packet is very likely to be valid, otherwise the packet must be corrupted

- Put the checksum back to the checksum field

**Check for duplicate segment**

For receiver, check whether there is already a segment in the receive buffer that contains equal sequence number as the received segment. if there is, then the segment is a duplicate

For sender, check whether there is any segment in the send buffer with sequence number equal to received segment’s ACK number that already marked as ACK’d. if there is, then the segment is a duplicate

**Check for missing/out of order packet**

For receiver, check whether sequence number of the received segment is equal to lastCumulativeAckNum, if not equal then the received segment is out of order

For sender, check whether ACK number of the received segment is equal to nextSeqNum, if not equal then the received segment is out of order

**MSS**

The RxP protocol implements pre-determined MSS, which will be MSS=576 bytes - 32 bytes = 544 bytes 

**Congestion Control**

Congestion Control implements the *Old Tahoe* algorithm. This algorithm increase the number of packets sent slowly when there is no congestion in the network, but once it encounters a problem, it drops the number of packets sent multiplicatively to avoid congestion.

*Updated API*
=============
``**rxpsocket()**: rxpsocket``
------------------------------

``Creates an unconnected RxP socket.``

    ``Parameter	: void``

    ``Return	:``
        ``rxpsocket a new RxP socket object.``

``**bind(address)**: void``
---------------------------

``Associates this socket with a port number.``
    
    ``Parameter	:``
        ``address a tuple that contains the IP address and port number to be associated with this socket.``
        
    ``Return	: void``

``**connect(address)**: void``
------------------------------

``Attempts to establish connection to the server.``

    ``Parameter	:``
        ``address a tuple that contains the IP address and port number.``

    ``Return	: void``

``**listen(maxQueuedConnections)**: void``
------------------------------------------

``Opens this socket for any incoming connection, with a maximum number of clients waiting to be connected specified in the parameter.``

    ``  Parameter	:``
        ``maxQueuedConnections the maximum number of clients that can queue to connect to the socket.``

    ``Return	: void``

``**accept()**: (rxpSocket, clientAddr)``
-----------------------------------------

``Creates a new socket that will further communicate with the client. The call to this method will block when there is no client waiting to be served by the server.``

    ``Parameter	: void``
    
    ``Return	:``
        ``(rxpSocket, clientAddr) a tuple that contains the new socket that is connected to the client and the client address.``

``**send(dataBytes)**: void``
-----------------------------

``Sends data by putting the data bytes in the socket.``

    ``Parameter	:``
        ``dataBytes the byte stream to be sent through the socket.``

    ``Return	: void``

``**recv(maxBytesRead)**: dataBytes``
-------------------------------------

``Returns the data byte array received by the socket. The data byte array contains up to a specified number of bytes. The call to this method will block when there are no data to be read, and will return NONE if the connection terminated unexpectedly.``

    ``Parameter	:``
        ``maxBytesRead the maximum number of bytes in the data byte array.``

    ``Return	:``
        ``dataBytes the byte array containing the data received by the socket.``

``**close()**: void``
---------------------

``Closes the connection of this socket by initiating three-way closing handshake.``

    ``Parameter	: void``
    
    ``Return	: void``

*Known Bugs and Limitations*
============================
