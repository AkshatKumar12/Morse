# anmol.py (client.py)

import sys
import socket
import threading
import pickle
import time
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QListWidget, QListWidgetItem,
    QInputDialog, QMessageBox, QCompleter # <-- Import QCompleter
)
from PyQt5.QtGui import QTextCursor, QFont, QColor
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QStringListModel # <-- Import QStringListModel

# Import your core encryption and compression functions
from core import encrypt_message, decrypt_message, huffman_compress, huffman_decompress
# Import database functions
from database import init_db, add_contact, get_contacts, save_message, get_messages, DB_NAME
# --- NEW: Import the Trie class ---
from trie import Trie

HOST = 'localhost'
PORT = 9999

# ... (ClientSignals and ClientWorker classes remain unchanged) ...

class ClientSignals(QObject):
    message_received = pyqtSignal(str, str, str) # message, sender_username, chat_partner_username
    server_message = pyqtSignal(str) # For system messages (e.g., connection status)
    connected_to_server = pyqtSignal(str) # Username
    disconnected_from_server = pyqtSignal()
    online_users_updated = pyqtSignal(list) # List of online usernames

class ClientWorker(QThread):
    def __init__(self, sock, username, signals):
        super().__init__()
        self.sock = sock
        self.username = username
        self.signals = signals
        self.running = True

    def run(self):
        try:
            # Initial handshake: send username to server
            self.sock.sendall(pickle.dumps(self.username))
            self.signals.server_message.emit(f"Connected as '{self.username}'. Waiting for online users...")

            # First message from server should be the online users list or an error
            initial_data = self.sock.recv(4096)
            if not initial_data:
                raise Exception("Server did not send initial online users list or error.")
            
            initial_packet = pickle.loads(initial_data)
            if initial_packet.get("type") == "ERROR": # Check for immediate server errors like duplicate username
                raise Exception(initial_packet["message"])
            elif initial_packet.get("type") == "online_users":
                self.signals.online_users_updated.emit(initial_packet["users"])
                self.signals.connected_to_server.emit(self.username)
            else:
                raise Exception("Unexpected initial packet from server.")


            while self.running:
                data = self.sock.recv(4096)
                if not data:
                    break # Server disconnected or socket closed

                message_packet = pickle.loads(data)
                
                if message_packet.get("type") == "chat_message":
                    sender = message_packet["sender"]
                    recipient = message_packet["recipient"] # This client's username
                    payload = message_packet["payload"]

                    compressed = payload["compressed"]
                    key_seed = payload["key_seed"]
                    tree = pickle.loads(payload["huffman_tree"])

                    decrypted_message = decrypt_message(huffman_decompress(compressed, tree), key_seed)
                    
                    # Determine chat_partner_username (the one whose chat is currently active)
                    chat_partner_username = sender # If message is from sender, then sender is the chat partner

                    self.signals.message_received.emit(decrypted_message, sender, chat_partner_username)
                elif message_packet.get("type") == "online_users":
                    self.signals.online_users_updated.emit(message_packet["users"])

        except (EOFError, ConnectionResetError, OSError) as e:
            self.signals.server_message.emit(f"Disconnected from server: {e}")
            self.signals.disconnected_from_server.emit()
        except Exception as e:
            self.signals.server_message.emit(f"Error in client worker: {e}")
            self.signals.disconnected_from_server.emit()
        finally:
            self.signals.server_message.emit("Client worker stopped.")
            # Socket will be closed by the main thread during cleanup

    def stop(self):
        self.running = False
        try:
            # Attempt a graceful shutdown if possible, but force close if needed
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass # Socket already closed or not connected

class ClientGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.username = self.get_username()
        if not self.username:
            sys.exit()

        # --- NEW: Initialize Trie and Completer Model ---
        self.trie = Trie()
        self.completer_model = QStringListModel()
        
        # Initialize database
        init_db()
        add_contact(self.username)

        self.setWindowTitle(f"💬 Messenger - {self.username}")
        self.setGeometry(950, 100, 900, 700)

        self.current_chat_partner = None
        self.client_socket = None
        self.client_thread = None

        self.init_ui()

        # --- NEW: Populate the Trie with words from chat history ---
        self.populate_trie_from_history()

        self.signals = ClientSignals()
        self.signals.message_received.connect(self.handle_message_received)
        self.signals.server_message.connect(lambda msg: self.append_chat(msg, "system"))
        self.signals.connected_to_server.connect(self.on_connected_to_server)
        self.signals.disconnected_from_server.connect(self.on_disconnected_from_server)
        self.signals.online_users_updated.connect(self.update_online_users)

        threading.Thread(target=self.connect_to_server_threaded, daemon=True).start()


    def get_username(self):
        username, ok = QInputDialog.getText(self, 'Username', 'Enter your username:')
        if ok and username.strip():
            return username.strip()
        else:
            QMessageBox.warning(self, "Warning", "Username cannot be empty. Exiting.")
            return None

    def init_ui(self):
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Left Panel: Contacts List ---
        # ... (This part is unchanged) ...
        left_panel_widget = QWidget()
        left_panel_layout = QVBoxLayout()
        left_panel_layout.setContentsMargins(0, 0, 0, 0)
        left_panel_layout.setSpacing(0)
        left_panel_widget.setLayout(left_panel_layout)
        left_panel_widget.setFixedWidth(280) # Fixed width for contacts
        left_panel_widget.setStyleSheet("background-color: #F8F9FA; border-right: 1px solid #E0E0E0;")
        self.contacts_header = QLabel("Chats")
        self.contacts_header.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.contacts_header.setAlignment(Qt.AlignCenter)
        self.contacts_header.setStyleSheet("padding: 20px; background-color: #E9ECEF; border-bottom: 1px solid #D1D5DA; color: #343A40;")
        left_panel_layout.addWidget(self.contacts_header)
        self.contact_list_widget = QListWidget()
        self.contact_list_widget.setFont(QFont("Segoe UI", 12))
        self.contact_list_widget.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: #F8F9FA;
            }
            QListWidget::item {
                padding: 15px 20px;
                border-bottom: 1px solid #E5E5E5;
                color: #343A40;
            }
            QListWidget::item:selected {
                background-color: #E0E7FF;
                color: #000000;
                font-weight: bold;
            }
            QListWidget::item:hover:!selected {
                background-color: #EFF2F5;
            }
        """)
        self.contact_list_widget.itemClicked.connect(self.load_chat)
        left_panel_layout.addWidget(self.contact_list_widget)
        self.add_contact_button = QPushButton("➕ Add Contact")
        self.add_contact_button.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.add_contact_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 12px 15px;
                border-radius: 8px;
                margin: 15px;
            }
            QPushButton:hover { background-color: #0056b3; }
            QPushButton:pressed { background-color: #00408C; }
        """)
        self.add_contact_button.clicked.connect(self.show_add_contact_dialog)
        left_panel_layout.addWidget(self.add_contact_button)
        main_layout.addWidget(left_panel_widget)
        
        # --- Right Panel: Chat Area ---
        # ... (This part is mostly unchanged) ...
        right_panel_widget = QWidget()
        right_panel_layout = QVBoxLayout()
        right_panel_layout.setContentsMargins(0, 0, 0, 0)
        right_panel_layout.setSpacing(0)
        right_panel_widget.setLayout(right_panel_layout)
        right_panel_widget.setStyleSheet("background-color: #FFFFFF;")
        self.chat_partner_header = QLabel("Select a chat to begin")
        self.chat_partner_header.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.chat_partner_header.setAlignment(Qt.AlignCenter)
        self.chat_partner_header.setStyleSheet("padding: 20px; background-color: #E9ECEF; border-bottom: 1px solid #D1D5DA; color: #343A40;")
        right_panel_layout.addWidget(self.chat_partner_header)
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Segoe UI", 11)) 
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #FDFDFD;
                border: none;
                padding: 15px;
                color: #343A40;
            }
        """)
        right_panel_layout.addWidget(self.chat_display)

        # Message input area
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(15, 10, 15, 15)
        input_layout.setSpacing(10)

        self.message_input = QLineEdit()
        self.message_input.setFont(QFont("Segoe UI", 11))
        self.message_input.setPlaceholderText("Type a message...")
        self.message_input.returnPressed.connect(self.send_message)
        self.message_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #D1D5DA;
                border-radius: 22px;
                padding: 10px 18px;
                background-color: white;
                color: #343A40;
            }
            QLineEdit:focus {
                border: 1px solid #007bff;
                outline: none;
            }
        """)

        # --- NEW: Setup QCompleter for text recommendations ---
        self.completer = QCompleter()
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setModel(self.completer_model)
        self.message_input.setCompleter(self.completer)

        # Connect signals for the recommendation system
        self.message_input.textChanged.connect(self.update_recommendations)
        self.completer.activated[str].connect(self.apply_recommendation)
        
        input_layout.addWidget(self.message_input)

        self.send_button = QPushButton("Send")
        self.send_button.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setFixedSize(85, 44)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 22px;
            }
            QPushButton:hover { background-color: #0056b3; }
            QPushButton:pressed { background-color: #00408C; }
            QPushButton:disabled {
                background-color: #E0E0E0;
                color: #A0A0A0;
            }
        """)
        self.send_button.setDisabled(True)
        input_layout.addWidget(self.send_button)
        right_panel_layout.addLayout(input_layout)
        main_layout.addWidget(right_panel_widget, 1)
        self.setLayout(main_layout)

        # ... (Chat display CSS is unchanged) ...
        self.chat_display.document().setDefaultStyleSheet("""
    body {
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 10.5pt;
        margin: 0;
        padding: 0;
    }
    .message-wrapper {
        display: flex;
        margin: 10px;
        clear: both;
    }
    .message-wrapper.their {
        justify-content: flex-start;
    }
    .message-wrapper.self {
        justify-content: flex-end;
    }
    .bubble {
        max-width: 65%;
        padding: 10px 14px;
        border-radius: 18px;
        background-color: #DCF8C6; /* self */
        color: #333;
        font-size: 10.5pt;
        line-height: 1.4;
        position: relative;
    }
    .message-wrapper.their .bubble {
        background-color: #F1F0F0;
    }
    .timestamp {
        font-size: 8pt;
        color: #888;
        text-align: right;
        margin-top: 5px;
    }
    .system-message {
        text-align: center;
        font-style: italic;
        color: #666;
        margin: 10px 0;
        font-size: 9.5pt;
    }
""")
        self.load_contacts_from_db()


    # --- NEW: Method to populate Trie from DB ---
    def populate_trie_from_history(self):
        """Loads all words from message history into the Trie."""
        print("Populating Trie from chat history...")
        try:
            all_contacts = get_contacts() 
            for contact_name in all_contacts:
                messages = get_messages(contact_name)
                for msg in messages:
                    # Split message content into words and insert into Trie
                    words = msg["content"].split()
                    for word in words:
                        self.trie.insert(word)
            print("Trie population complete.")
        except Exception as e:
            print(f"Could not populate Trie from database: {e}")

    # --- NEW: Method to update completer suggestions ---
    def update_recommendations(self, text):
        """Updates the list of suggestions in the completer."""
        if ' ' in text:
            # Get the last word being typed
            last_word = text.split(' ')[-1]
        else:
            last_word = text

        if not last_word:
            self.completer_model.setStringList([])
            return
            
        recommendations = self.trie.search_prefix(last_word)
        self.completer_model.setStringList(recommendations)

    # --- NEW: Method to apply a selected recommendation ---
    def apply_recommendation(self, completed_word):
        """Replaces the last typed word with the selected recommendation."""
        current_text = self.message_input.text()
        words = current_text.split(' ')
        base_text = ' '.join(words[:-1])
        
        # Append the completed word with a space for a better user experience
        if base_text:
            new_text = base_text + ' ' + completed_word + ' '
        else:
            new_text = completed_word + ' '
            
        self.message_input.setText(new_text)
        self.message_input.setCursorPosition(len(new_text))

    def load_contacts_from_db(self):
        # ... (Unchanged) ...
        self.contact_list_widget.clear()
        contacts = get_contacts()
        for contact in contacts:
            if contact != self.username: # Don't add self to contact list
                item = QListWidgetItem(contact)
                self.contact_list_widget.addItem(item)
        
        if self.contact_list_widget.count() > 0:
            self.contact_list_widget.setCurrentRow(0)
            self.load_chat(self.contact_list_widget.currentItem())

    def show_add_contact_dialog(self):
        # ... (Unchanged) ...
        contact_name, ok = QInputDialog.getText(self, 'Add New Contact', 'Enter username of new contact:')
        if ok and contact_name.strip():
            contact_name = contact_name.strip()
            if contact_name == self.username:
                QMessageBox.warning(self, "Invalid Contact", "Cannot add yourself as a contact.")
                return
            if add_contact(contact_name):
                QMessageBox.information(self, "Success", f"Contact '{contact_name}' added.")
                self.load_contacts_from_db()
            else:
                QMessageBox.warning(self, "Exists", f"Contact '{contact_name}' already exists.")

    def connect_to_server_threaded(self):
        # ... (Unchanged) ...
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(5.0)
            self.client_socket.connect((HOST, PORT))
            self.client_socket.settimeout(None)

            self.client_thread = ClientWorker(self.client_socket, self.username, self.signals)
            self.client_thread.start()
        except socket.timeout:
            self.signals.server_message.emit(f"Connection timed out. Server not responding on {HOST}:{PORT}.")
        except ConnectionRefusedError:
            self.signals.server_message.emit(f"Connection refused. Is the server running on {HOST}:{PORT}?")
        except Exception as e:
            self.signals.server_message.emit(f"Error connecting to server: {e}")

    def on_connected_to_server(self, username):
        # ... (Unchanged) ...
        self.append_chat(f"Connected to server as '{username}'.", "system")
        if self.current_chat_partner:
            self.send_button.setDisabled(False)

    def on_disconnected_from_server(self):
        # ... (Unchanged) ...
        self.append_chat("Disconnected from server.", "system")
        if self.client_thread and self.client_thread.isRunning():
            self.client_thread.stop()
            self.client_thread.wait(100)
        if self.client_socket:
            try:
                self.client_socket.close()
            except OSError:
                pass
        self.client_socket = None
        self.client_thread = None
        self.send_button.setDisabled(True)

    def update_online_users(self, online_users):
        # ... (Unchanged) ...
        self.append_chat(f"Online users: {', '.join(online_users)}", "system")

    def load_chat(self, item):
        # ... (Unchanged) ...
        for i in range(self.contact_list_widget.count()):
            list_item = self.contact_list_widget.item(i)
            font = list_item.font()
            font.setBold(False)
            list_item.setFont(font)
        
        self.contact_list_widget.setCurrentItem(item)
        self.current_chat_partner = item.text()
        self.chat_partner_header.setText(self.current_chat_partner)
        self.chat_display.clear()
        
        if self.client_socket and self.client_socket.fileno() != -1: 
            self.send_button.setEnabled(True)
        else:
            self.send_button.setEnabled(False)

        messages = get_messages(self.current_chat_partner)
        for msg in messages:
            if msg["is_sent_by_me"]:
                self.append_chat(msg["content"], "self", msg["timestamp"])
            else:
                self.append_chat(msg["content"], "their", msg["timestamp"])
        
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.chat_display.setTextCursor(cursor)

    def handle_message_received(self, message_content, sender_username, chat_partner_username_ignored):
        # ... (Unchanged) ...
        save_message(sender_username, sender_username, self.username, message_content, False)
        if self.current_chat_partner == sender_username:
            self.append_chat(message_content, "their")
        else:
            print(f"New message from {sender_username}: {message_content}")
            for item_index in range(self.contact_list_widget.count()):
                item = self.contact_list_widget.item(item_index)
                if item.text() == sender_username:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                    break

    def send_message(self):
        msg = self.message_input.text().strip()
        if not msg:
            return

        if not self.current_chat_partner:
            QMessageBox.warning(self, "No Chat Selected", "Please select a contact to send a message to.")
            return

        if not self.client_socket or self.client_socket.fileno() == -1:
            self.append_chat("Not connected to server. Please check your connection.", "system")
            self.send_button.setDisabled(True)
            return

        try:
            encrypted_payload, key_seed = encrypt_message(msg)
            compressed_payload, tree = huffman_compress(encrypted_payload)

            packet_to_server = {
                "type": "chat_message",
                "sender": self.username,
                "recipient": self.current_chat_partner,
                "payload": {
                    "compressed": compressed_payload,
                    "key_seed": key_seed,
                    "huffman_tree": pickle.dumps(tree)
                }
            }
            self.client_socket.sendall(pickle.dumps(packet_to_server))
            
            save_message(self.current_chat_partner, self.username, self.current_chat_partner, msg, True)

            # --- MODIFIED: Update Trie with new words from the sent message ---
            words_in_msg = msg.split()
            for word in words_in_msg:
                self.trie.insert(word)

            self.append_chat(msg, "self")
            self.message_input.clear()
        except OSError as e:
            self.append_chat(f"Network error sending message: {e}", "system")
            QMessageBox.critical(self, "Network Error", f"Failed to send message: {e}\nConnection might be lost.")
            self.on_disconnected_from_server()
        except Exception as e:
            self.append_chat(f"Error sending message: {e}", "system")
            QMessageBox.critical(self, "Send Error", f"Failed to send message: {e}")

    def append_chat(self, msg, sender_type, timestamp=None):
        # ... (Unchanged) ...
        if timestamp is None:
            timestamp = time.strftime("%H:%M")

        if sender_type == "self":
            html_msg = f"""
        <div class="message-wrapper self">
            <div class="bubble">
                {msg}
                <div class="timestamp">{timestamp}</div>
            </div>
        </div>
        """
        elif sender_type == "their":
            html_msg = f"""
        <div class="message-wrapper their">
            <div class="bubble">
                {msg}
                <div class="timestamp">{timestamp}</div>
            </div>
        </div>
        """
        else:
            html_msg = f'<div class="system-message">{msg}</div>'

        self.chat_display.insertHtml(html_msg)
        self.chat_display.insertHtml("<br>")
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.chat_display.setTextCursor(cursor)

    def closeEvent(self, event):
        # ... (Unchanged) ...
        self.close_connections()
        event.accept()

    def close_connections(self):
        # ... (Unchanged) ...
        if self.client_thread and self.client_thread.isRunning():
            self.client_thread.stop()
            self.client_thread.wait(1000)
        if self.client_socket:
            try:
                self.client_socket.close()
            except OSError:
                pass
        print(f"Client '{self.username}' connections closed.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    client_gui = ClientGUI()
    client_gui.show()
    sys.exit(app.exec_())