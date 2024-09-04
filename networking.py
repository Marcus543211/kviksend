import socket
import pickle
from threading import Thread
from time import sleep

SLEEP_TIME = 0.1


class Address:
    def __init__(self, ip_address: str, port: int):
        self.ip_address = ip_address
        self.port = port

    def as_tuple(self):
        return (self.ip_address, self.port)

    def __str__(self):
        return f'{self.ip_address}:{self.port}'

    def __repr__(self):
        return f'Address({self.ip_address}, {self.port})'


class Server:
    def __init__(self):
        self.is_running = True
        self.address = None

        self.thread = Thread(target=self._server)
        self.thread.start()

    def get_address(self) -> Address:
        """Gets the IP-address and port of the server"""
        # Wait for the other thread to select an address
        while not self.address:
            sleep(SLEEP_TIME)

        return self.address

    def get_clients(self):
        """Gets the IP-addresses for all connected clients"""
        return list(self.clients.keys())

    def close(self):
        """Closes the server"""
        self.is_running = False
        self.thread.join()

    def _server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            address = socket.gethostbyname(socket.gethostname())

            sock.bind((address, 0))
            sock.listen()
            sock.setblocking(False)

            self.address = Address(*sock.getsockname())

            self.clients = {}

            while self.is_running:
                sleep(SLEEP_TIME)

                dead_clients = []
                messages = []

                # Accept new connections
                try:
                    conn, addr = sock.accept()
                except BlockingIOError:
                    pass
                else:
                    addr = Address(*addr)
                    pickler, unpickler = pickle_socket(conn)
                    self.clients[addr] = (conn, pickler, unpickler)

                # Check for messages
                for addr, (_, _, unpickler) in self.clients.items():
                    try:
                        obj = unpickler.load()
                    except TypeError:
                        pass
                    except EOFError:
                        dead_clients.append(addr)
                    else:
                        messages.append((addr, obj))

                # Remove dead clients
                for addr in dead_clients:
                    self.clients[addr][0].close()
                    del self.clients[addr]

                # Send messages
                for message in messages:
                    for _, pickler, _ in self.clients.values():
                        pickler.dump(message)


class Client:
    def __init__(self, address: Address, handle):
        self.is_running = True
        self.handle = handle

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(address.as_tuple())
        self.sock.setblocking(False)

        self.pickler, self.unpickler = pickle_socket(self.sock)

        self.thread = Thread(target=self._recive)
        self.thread.start()

    def send(self, obj):
        """Sends the object"""
        self.pickler.dump(obj)

    def get_address(self):
        """Gets the IP-address and port"""
        return Address(*self.sock.getsockname())

    def close(self):
        """Disconnects the client"""
        self.is_running = False
        self.sock.close()

        try:
            self.thread.join()
        except RuntimeError:
            pass

    def _recive(self):
        while self.is_running:
            sleep(SLEEP_TIME)

            try:
                addr, obj = self.unpickler.load()
            except TypeError:
                # No messages
                pass
            except EOFError:
                # Server quit
                break
            else:
                self.handle(addr, obj)


def pickle_socket(sock):
    write_file = sock.makefile('bw', 0)
    pickler = pickle.Pickler(write_file)

    read_file = sock.makefile('br', 0)
    unpickler = pickle.Unpickler(read_file)

    return pickler, unpickler
