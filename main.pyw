from dataclasses import dataclass
from time import sleep

import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from tkinter.simpledialog import askstring

from networking import Server, Client, Address


class NetworkCommand:
    pass


@dataclass
class RelocateHost(NetworkCommand):
    """
    Sent when the host is leaving to prepare a relocation.
    Contains the address of the next host.
    """
    new_host: Address


@dataclass
class NewHost(NetworkCommand):
    """Sent by the new host when he has opened a server"""
    address: Address


@dataclass
class Message(NetworkCommand):
    """Just a text message"""
    text: str


class Chat(ttk.Frame):
    def __init__(self, master, address=None):
        super().__init__(master)

        if address:
            self.address = address
        else:
            # Host if not given an address
            self.server = Server(Address('0.0.0.0', 0))
            port = self.server.get_address().port
            self.address = Address('127.0.0.1', port)

        self.client = Client(self.address, self.handle_message)
        self.closing = False

        self.bind('<Destroy>', self.on_destroy)

        self.text = ScrolledText(self, state=tk.DISABLED)
        self.message_entry = ttk.Entry(self)
        self.send_button = ttk.Button(
            self, text='Send', command=self.send_message)

        self.message_entry.bind('<Return>', lambda _: self.send_message())

        self.text.grid(row=1, column=0, columnspan=2, sticky='NSEW')
        self.message_entry.grid(row=2, column=0, columnspan=1, sticky='EW')
        self.send_button.grid(row=2, column=1)

    def handle_message(self, addr, message):
        if self.closing:
            return

        if isinstance(message, Message):
            self.text.config(state=tk.NORMAL)
            self.text.insert(tk.END, f'{addr} > {message.text}\n')
            self.text.config(state=tk.DISABLED)

        elif isinstance(message, RelocateHost) \
                and message.new_host == self.client.get_address():
            self.server = Server()
            self.client.send(NewHost(self.server.get_address()))

        elif isinstance(message, NewHost):
            self.client.close()
            self.client = Client(message.address, self.handle_message)

    def send_message(self):
        message = self.message_entry.get()
        if message:
            self.message_entry.delete(0, tk.END)
            self.client.send(Message(message))

    def on_destroy(self, event):
        if hasattr(self, 'server'):
            # Relocate to a new host
            my_address = self.client.get_address()
            clients = filter(lambda address: my_address != address,
                             self.server.get_clients())

            try:
                new_host = next(clients)
            except StopIteration:
                # There were no others connected
                pass
            else:
                self.client.send(RelocateHost(new_host))

                # Wait for all clients to disconnect
                while len(self.server.get_clients()) > 1:
                    sleep(0.1)

            self.server.close()

        self.client.close()


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title('Test')
        self.geometry('800x600')

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH)

        self.host_tab = ttk.Frame(self)
        self.join_tab = ttk.Frame(self)
        self.notebook.add(self.host_tab, text='<Host>')
        self.notebook.add(self.join_tab, text='<Join>')

        self.notebook.bind('<<NotebookTabChanged>>', self.switched_tab)

        self.chats = []
        self.host()

    def switched_tab(self, event):
        tab = self.notebook.index('current')
        if tab == self.notebook.index(self.host_tab):
            self.host()
        elif tab == self.notebook.index(self.join_tab):
            self.join()

    def join(self):
        address = askstring('Join', 'Enter the address that you want to join:')

        address, port = address.split(':')
        self.add_chat(Address(address, int(port)))

    def host(self):
        self.add_chat(None)

    def add_chat(self, address):
        chat = Chat(self, address)
        self.chats.append(chat)

        # Make sure join and host are always the last tabs
        pos = self.notebook.index('end') - 2
        self.notebook.insert(pos, chat, text=f'{chat.address}')
        self.notebook.select(pos)


def main():
    app = App()
    app.mainloop()


if __name__ == '__main__':
    main()
