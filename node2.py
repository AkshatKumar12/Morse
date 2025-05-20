import socket
import threading
import tkinter as tk
from tkinter import scrolledtext
import pickle
from core import encrypt_message, decrypt_message, huffman_compress, huffman_decompress

HOST = 'localhost'
PORT = 9999

class ClientGUI:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("🟢 Client")
        self.window.geometry("500x500")

        self.chat = scrolledtext.ScrolledText(self.window, state='disabled', font=("Courier", 10))
        self.chat.pack(padx=10, pady=10, fill='both', expand=True)
        self.chat.tag_config("server", foreground="blue")
        self.chat.tag_config("client", foreground="green")
        self.chat.tag_config("self", foreground="black")

        self.entry = tk.Entry(self.window, font=("Courier", 12))
        self.entry.pack(padx=10, pady=5, fill='x')
        self.entry.bind("<Return>", self.send_message)

        self.connect_to_server()
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.window.mainloop()

    def connect_to_server(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((HOST, PORT))
        self.append_chat("[Connected to Server]", "client")
        threading.Thread(target=self.receive, daemon=True).start()

    def receive(self):
        while True:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break
                packet = pickle.loads(data)
                compressed = packet["compressed"]
                key_seed = packet["key_seed"]
                tree = pickle.loads(packet["huffman_tree"])
                decrypted = decrypt_message(huffman_decompress(compressed, tree), key_seed)
                self.append_chat(f"[Server 📨] {decrypted}", "server")
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
            self.sock.sendall(pickle.dumps(packet))
            self.append_chat(f"[You 💬] {msg}", "self")
            self.entry.delete(0, tk.END)

    def append_chat(self, msg, tag):
        self.chat.config(state='normal')
        self.chat.insert(tk.END, msg + '\n', tag)
        self.chat.config(state='disabled')
        self.chat.yview(tk.END)

    def close(self):
        self.sock.close()
        self.window.destroy()

if __name__ == '__main__':
    ClientGUI()
