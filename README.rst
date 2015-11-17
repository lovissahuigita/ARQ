:Authors: Lovissa Winyoto (lwinyoto3@gatech.edu), Yoel Ivan (yivan3@gatech.edu)

====================================
**RxP** - Reliable Transfer Protocol
====================================

===================================
**FxA** - File Transfer Application
===================================

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
