# server.py
import sys
import socket
import threading
import pickle
import time
from collections import defaultdict
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QLabel, QLineEdit, QPushButton
from PyQt5.QtGui import QFont, QTextCursor
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject

HOST = '0.0.0.0' # Listen on all available interfaces
PORT = 9999

# Global dictionary to store connected clients: {username: socket_object}
CONNECTED_CLIENTS = {}
# Lock for thread-safe access to CONNECTED_CLIENTS
CLIENTS_LOCK = threading.Lock()

# Custom Signal class for server GUI updates
class ServerSignals(QObject):
    log_message = pyqtSignal(str) # For server internal logs
    client_connected = pyqtSignal(str) # When a new client connects
    client_disconnected = pyqtSignal(str) # When a client disconnects

class ClientHandler(QThread):
    def __init__(self, conn, addr, signals):
        super().__init__()
        self.conn = conn
        self.addr = addr
        self.username = None # Will be set after initial handshake
        self.signals = signals
        self.running = True

    def run(self):
        try:
            # Initial handshake: receive username
            username_packet = self.conn.recv(1024)
            if not username_packet:
                raise Exception("Did not receive username handshake.")
            self.username = pickle.loads(username_packet)

            with CLIENTS_LOCK:
                if self.username in CONNECTED_CLIENTS:
                    # Duplicate username, reject
                    self.conn.sendall(pickle.dumps("ERROR: Username already taken."))
                    raise Exception(f"Duplicate username attempt: {self.username}")
                CONNECTED_CLIENTS[self.username] = self.conn
            self.signals.client_connected.emit(self.username)
            self.signals.log_message.emit(f"Client {self.username} ({self.addr}) connected.")

            # Send current list of online users to the new client
            with CLIENTS_LOCK:
                online_users = list(CONNECTED_CLIENTS.keys())
            self.conn.sendall(pickle.dumps({"type": "online_users", "users": online_users}))


            while self.running:
                data = self.conn.recv(4096)
                if not data:
                    break # Client disconnected
                
                message_packet = pickle.loads(data)
                
                # Expected packet format: {"type": "chat_message", "sender": "user1", "recipient": "user2", "payload": {compressed, key_seed, huffman_tree}}
                if message_packet.get("type") == "chat_message":
                    sender = message_packet["sender"]
                    recipient = message_packet["recipient"]
                    payload = message_packet["payload"]

                # Log the raw encrypted message for showoff
                    compressed_preview = payload.get("compressed", "")[:60] + "..." if len(payload.get("compressed", "")) > 60 else payload.get("compressed", "");key_seed = payload.get("key_seed", "");self.signals.log_message.emit(f"Encrypted from {sender} → {recipient}:\n    Compressed: {compressed_preview}\n    Key Seed: {key_seed}")



                    with CLIENTS_LOCK:
                        recipient_socket = CONNECTED_CLIENTS.get(recipient)

                    if recipient_socket:
                        try:
                            # Forward the exact packet (payload already encrypted/compressed)
                            recipient_socket.sendall(pickle.dumps(message_packet))
                            self.signals.log_message.emit(f"Message relayed from {sender} to {recipient}.")
                        except OSError as e:
                            self.signals.log_message.emit(f"Failed to relay to {recipient}: {e}")
                            # Consider removing recipient if their socket is broken
                    else:
                        self.signals.log_message.emit(f"Recipient {recipient} not found/online.")
                        # Optionally, send a delivery failure message back to sender

        except (EOFError, ConnectionResetError, OSError) as e:
            self.signals.log_message.emit(f"Client {self.username if self.username else self.addr} disconnected unexpectedly: {e}")
        except Exception as e:
            self.signals.log_message.emit(f"Error handling client {self.username if self.username else self.addr}: {e}")
        finally:
            if self.username:
                with CLIENTS_LOCK:
                    if self.username in CONNECTED_CLIENTS:
                        del CONNECTED_CLIENTS[self.username]
                self.signals.client_disconnected.emit(self.username)
                self.signals.log_message.emit(f"Client {self.username} removed from active connections.")
            try:
                self.conn.close()
            except OSError:
                pass # Already closed

    def stop(self):
        self.running = False
        try:
            self.conn.shutdown(socket.SHUT_RDWR)
            self.conn.close()
        except OSError:
            pass # Already closed or not connected

class ServerGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔗 Central Server")
        self.setGeometry(100, 100, 600, 500)
        self.init_ui()
        self.listening_socket = None
        self.client_threads = [] # Keep track of client handler threads

        self.signals = ServerSignals()
        self.signals.log_message.connect(self.append_log)
        self.signals.client_connected.connect(self.handle_client_connected)
        self.signals.client_disconnected.connect(self.handle_client_disconnected)

        self.start_server()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        self.title_label = QLabel("Server Log")
        self.title_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("color: #333; margin-bottom: 10px;")
        main_layout.addWidget(self.title_label)

        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Consolas", 10))
        self.log_display.setStyleSheet("""
            QTextEdit {
                background-color: #f8f8f8;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                padding: 10px;
                color: #444;
            }
        """)
        main_layout.addWidget(self.log_display)

        self.status_label = QLabel("Status: Not Running")
        self.status_label.setFont(QFont("Arial", 12))
        self.status_label.setStyleSheet("color: #555;")
        main_layout.addWidget(self.status_label)

        self.setLayout(main_layout)

    def start_server(self):
        try:
            self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.listening_socket.settimeout(0.5) # Non-blocking accept for graceful shutdown
            self.listening_socket.bind((HOST, PORT))
            self.listening_socket.listen(5) # Allow up to 5 pending connections
            self.status_label.setText(f"Status: Listening on {HOST}:{PORT}")
            self.append_log(f"Server started, listening on {HOST}:{PORT}")
            threading.Thread(target=self._accept_clients_loop, daemon=True).start()
        except OSError as e:
            self.status_label.setText("Status: Error starting server")
            self.append_log(f"ERROR: Could not start server: {e}")

    def _accept_clients_loop(self):
        while True:
            try:
                conn, addr = self.listening_socket.accept()
                client_thread = ClientHandler(conn, addr, self.signals)
                client_thread.start()
                self.client_threads.append(client_thread)
            except socket.timeout:
                continue # No new connection in timeout period, check if still running
            except OSError as e:
                self.append_log(f"ERROR in accept loop: {e}")
                break # Break loop on critical socket error

    def handle_client_connected(self, username):
        self.append_log(f"Client '{username}' connected. Total clients: {len(CONNECTED_CLIENTS)}")

    def handle_client_disconnected(self, username):
        self.append_log(f"Client '{username}' disconnected. Total clients: {len(CONNECTED_CLIENTS)}")
        # Clean up finished threads
        self.client_threads = [t for t in self.client_threads if t.isRunning()]

    def append_log(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        self.log_display.append(f"[{timestamp}] {msg}")
        cursor = self.log_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_display.setTextCursor(cursor)

    def closeEvent(self, event):
        self.close_connections()
        event.accept()

    def close_connections(self):
        self.append_log("Shutting down server...")
        # Stop all client threads
        for thread in self.client_threads:
            if thread.isRunning():
                thread.stop()
                thread.wait(100) # Give it a moment to stop

        # Close the listening socket
        if self.listening_socket:
            try:
                self.listening_socket.close()
            except OSError:
                pass
        self.status_label.setText("Status: Shut Down")
        self.append_log("Server shut down.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    server_gui = ServerGUI()
    server_gui.show()
    sys.exit(app.exec_())