import socket
import threading
import tkinter as tk
from tkinter import scrolledtext
import pickle
from core import encrypt_message, decrypt_message, huffman_compress, huffman_decompress

HOST = 'localhost'
PORT = 9999

class ServerGUI:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("🔵 Server")
        self.window.geometry("500x500")

        self.chat = scrolledtext.ScrolledText(self.window, state='disabled', font=("Courier", 10))
        self.chat.pack(padx=10, pady=10, fill='both', expand=True)
        self.chat.tag_config("server", foreground="blue")
        self.chat.tag_config("client", foreground="green")
        self.chat.tag_config("self", foreground="black")

        self.entry = tk.Entry(self.window, font=("Courier", 12))
        self.entry.pack(padx=10, pady=5, fill='x')
        self.entry.bind("<Return>", self.send_message)

        self.start_server()
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.window.mainloop()

    def start_server(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((HOST, PORT))
        self.sock.listen(1)
        threading.Thread(target=self.accept_client, daemon=True).start()

    def accept_client(self):
        self.conn, self.addr = self.sock.accept()
        self.append_chat(f"[Connected to client at {self.addr}]", "server")
        threading.Thread(target=self.receive, daemon=True).start()

    def receive(self):
        while True:
            try:
                data = self.conn.recv(4096)
                if not data:
                    break
                packet = pickle.loads(data)
                compressed = packet["compressed"]
                key_seed = packet["key_seed"]
                tree = pickle.loads(packet["huffman_tree"])
                decrypted = decrypt_message(huffman_decompress(compressed, tree), key_seed)
                self.append_chat(f"[Client 📨] {decrypted}", "client")
            except:
                break

    def send_message(self, event):
        msg = self.entry.get()
        if msg:
            encrypted, key_seed = encrypt_message(msg)
            compressed, tree = huffman_compress(encrypted)
            packet = {
                "compressed": compressed,
                "key_seed": key_seed,
                "huffman_tree": pickle.dumps(tree)
            }
            self.conn.sendall(pickle.dumps(packet))
            self.append_chat(f"[You 💬] {msg}", "self")
            self.entry.delete(0, tk.END)

    def append_chat(self, msg, tag):
        self.chat.config(state='normal')
        self.chat.insert(tk.END, msg + '\n', tag)
        self.chat.config(state='disabled')
        self.chat.yview(tk.END)

    def close(self):
        try:
            self.conn.close()
        except:
            pass
        self.sock.close()
        self.window.destroy()

if __name__ == '__main__':
    ServerGUI()
