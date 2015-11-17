import argparse
import logging
import re
from threading import Thread
from FxA.sock import sock
from FxA.util import Util
from exception import NoMoreMessage, RxPException

__logger = None
__socket = None
__serving_thread = None
__terminated = False


def main():
    parser = setup_cl_parser()
    args = parser.parse_args()

    # need to redeclare to write to global vars
    global __logger
    global __socket
    global __serving_thread

    __logger = Util.setup_logger()
    if args.verbose:
        __logger.setLevel(logging.DEBUG)
    else:
        __logger.setLevel(logging.ERROR)
    port_num, ne_addr = Util.parse_args(args.X, args.A, args.P)
    if port_num % 2 == 0:
        Util.exit_error('X has to be odd number')

    sock.initial_setup(port_num, ne_addr)
    __socket = sock()
    __socket.bind(('', 8000))
    __socket.listen(65535)
    __serving_thread = Thread(None, serve_client, 'client-server')
    help_message()
    __serving_thread.start()
    prompt_user_command()


__client_command_dict = {
    'POST': Util.download,
    'GET' : Util.upload
}


def proccess_client(client_sock, msg):
    msg = re.split('\s+', msg, maxsplit=1)
    __logger.debug(str(msg))
    if msg[0] in __client_command_dict:
        __client_command_dict.get(msg[0])(client_sock, msg[1] if len(msg) > 1
        else '')
    else:
        pass


def serve_client():
    while True:
        if __terminated:
            break

        client_addr = None

        try:
            print('Waiting for client...')
            served_socket, client_addr = __socket.accept()
            print('Serving ' + str(client_addr))
            while True:
                decoded = Util.recv_msg(served_socket)
                print(decoded)
                proccess_client(served_socket, decoded)
        except RxPException as err:
            if err.errno() == 103:
                print('stop listening...')
                break
            else:
                print(Util.ERROR_TAG + str(err))
        except NoMoreMessage:
            pass
        print('Finished serving ' + str(client_addr))
        print('Closing socket ' + str(served_socket))
        served_socket.close()


def help_message():
    print('Type \'help\' for list of command, \'terminate\' to quit.')


def command_wind(W):
    pass


# this is still very very wrong need confirmation on what it does!
def command_term(*_):
    __logger.info('running command \'terminate\'')
    __socket.close()
    # make sure all serving thread is done serving
    global __terminated
    __terminated = True
    print('waiting for serving thread...')
    __serving_thread.join()
    print('exitting...')
    exit()


def command_help(*_):
    __logger.info('running command \'help\'')
    print('Commands:')
    print('\twindow W\t\tconfigure maximum receiver window size for the '
          'server (in segments)')
    print('\tterminate\t\tshut down FxA-Server gracefully')
    print('\thelp\t\t\tprint this help message')


__command_dict = {
    'window'   : command_wind,
    'terminate': command_term,
    'help'     : command_help,
}


def prompt_user_command():
    while True:
        user_input = re.split('\s+', input('').strip(),
                              maxsplit=1)
        __logger.debug(str(user_input))
        if user_input[0] in __command_dict:
            __command_dict.get(user_input[0])(
                user_input[1] if len(user_input) > 1 else '')
        else:
            print(Util.ERROR_TAG + 'Invalid command \'' + str(user_input[0])
                  + '\'')
            help_message()


def setup_cl_parser():
    parser = argparse.ArgumentParser(description='Parse command-line '
                                                 'arguments')
    parser.add_argument('X', type=int, help='port number at which the '
                                            'FxA-server’s UDP socket '
                                            'should bind to (odd number)')
    parser.add_argument('A', type=str, help='the IP address of NetEmu')
    parser.add_argument('P', type=int, help='UDP port number of NetEmu')

    # action store_true to make the the args.verbose == false if not specified
    parser.add_argument('-v', '--verbose', help='print out process messages',
                        action='store_true')
    return parser


if __name__ == "__main__":
    main()
