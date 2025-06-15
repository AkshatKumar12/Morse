# client.py
import sys
import socket
import threading
import pickle
import time
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QListWidget, QListWidgetItem,
    QInputDialog, QMessageBox
)
from PyQt5.QtGui import QTextCursor, QFont, QColor
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject

# Import your core encryption and compression functions
from core import encrypt_message, decrypt_message, huffman_compress, huffman_decompress
# Import database functions
from database import init_db, add_contact, get_contacts, save_message, get_messages, DB_NAME

HOST = 'localhost'
PORT = 9999

# Custom Signal class for Client GUI updates (from worker thread)
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
            sys.exit() # Exit if user cancels username input

        # Initialize database
        init_db()
        add_contact(self.username) # Add self to contacts (for internal chat logic)

        self.setWindowTitle(f"💬 Messenger - {self.username}")
        self.setGeometry(950, 100, 900, 650) # Wider window

        self.current_chat_partner = None # The contact whose chat is currently open

        # --- FIX: Initialize client_socket and client_thread BEFORE init_ui() ---
        self.client_socket = None
        self.client_thread = None
        # --- END FIX ---

        self.init_ui() # Now, when init_ui is called, these attributes exist

        self.signals = ClientSignals()
        self.signals.message_received.connect(self.handle_message_received)
        self.signals.server_message.connect(lambda msg: self.append_chat(msg, "system"))
        self.signals.connected_to_server.connect(self.on_connected_to_server)
        self.signals.disconnected_from_server.connect(self.on_disconnected_from_server)
        self.signals.online_users_updated.connect(self.update_online_users)

        # Attempt to connect to server on startup
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
        main_layout.setContentsMargins(0, 0, 0, 0) # No margins for the main layout
        main_layout.setSpacing(0) # No spacing between panels

        # --- Left Panel: Contacts List ---
        left_panel_widget = QWidget()
        left_panel_layout = QVBoxLayout()
        left_panel_layout.setContentsMargins(0, 0, 0, 0)
        left_panel_layout.setSpacing(0)
        left_panel_widget.setLayout(left_panel_layout)
        left_panel_widget.setFixedWidth(280) # Fixed width for contacts
        left_panel_widget.setStyleSheet("background-color: #f2f2f2; border-right: 1px solid #e0e0e0;")

        self.contacts_header = QLabel("Chats")
        self.contacts_header.setFont(QFont("Segoe UI", 15, QFont.Bold))
        self.contacts_header.setAlignment(Qt.AlignCenter)
        self.contacts_header.setStyleSheet("padding: 15px; background-color: #e6e6e6; border-bottom: 1px solid #d0d0d0;")
        left_panel_layout.addWidget(self.contacts_header)

        self.contact_list_widget = QListWidget()
        self.contact_list_widget.setFont(QFont("Segoe UI", 12))
        self.contact_list_widget.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: #f8f8f8;
            }
            QListWidget::item {
                padding: 12px 15px;
                border-bottom: 1px solid #ebebeb;
            }
            QListWidget::item:selected {
                background-color: #e0e0e0;
                color: #333;
            }
            QListWidget::item:hover:!selected {
                background-color: #f0f0f0;
            }
        """)
        self.contact_list_widget.itemClicked.connect(self.load_chat)
        left_panel_layout.addWidget(self.contact_list_widget)

        self.add_contact_button = QPushButton("+ Add Contact")
        self.add_contact_button.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.add_contact_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; /* Green */
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                margin: 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.add_contact_button.clicked.connect(self.show_add_contact_dialog)
        left_panel_layout.addWidget(self.add_contact_button)

        main_layout.addWidget(left_panel_widget)

        # --- Right Panel: Chat Area ---
        right_panel_widget = QWidget()
        right_panel_layout = QVBoxLayout()
        right_panel_layout.setContentsMargins(0, 0, 0, 0)
        right_panel_layout.setSpacing(0)
        right_panel_widget.setLayout(right_panel_layout)
        right_panel_widget.setStyleSheet("background-color: #ffffff;") # White background for chat area

        self.chat_partner_header = QLabel("Select a chat to begin")
        self.chat_partner_header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.chat_partner_header.setAlignment(Qt.AlignCenter)
        self.chat_partner_header.setStyleSheet("padding: 15px; background-color: #e6e6e6; border-bottom: 1px solid #d0d0d0;")
        right_panel_layout.addWidget(self.chat_partner_header)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Segoe UI", 10))
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #fdfdfd; /* Lighter background */
                border: none;
                padding: 15px;
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
                border: 1px solid #ccc;
                border-radius: 20px;
                padding: 8px 15px;
                background-color: white;
            }
        """)
        input_layout.addWidget(self.message_input)

        self.send_button = QPushButton("Send")
        self.send_button.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setFixedSize(80, 40)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff; /* Blue */
                color: white;
                border: none;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.send_button.setDisabled(True) # Disabled until a chat is selected
        input_layout.addWidget(self.send_button)

        right_panel_layout.addLayout(input_layout)
        main_layout.addWidget(right_panel_widget, 1) # Right panel takes remaining space

        self.setLayout(main_layout)

        # Define HTML/CSS styles for chat messages (not strict bubbles)
        self.chat_display.document().setDefaultStyleSheet("""
            body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 10pt; margin: 0; padding: 0; }
            .message-wrapper {
                margin-bottom: 8px; /* Space between messages */
                overflow: hidden; /* Contains floats */
            }
            .message-content {
                padding: 10px 15px;
                border-radius: 15px; /* Softer rounded corners */
                max-width: 75%; /* Limit width */
                word-wrap: break-word;
                font-size: 10.5pt;
                line-height: 1.4;
                float: left; /* Default float for incoming */
            }
            .message-timestamp {
                font-size: 8pt;
                color: #888;
                margin-top: 3px;
                display: block; /* Ensures timestamp is on its own line within the content */
                text-align: right; /* Default for timestamp within content */
            }

            .my-message .message-content {
                background-color: #d1e7dd; /* Light green-blue */
                float: right; /* Push to right */
                color: #333;
            }
            .my-message .message-timestamp {
                color: #666;
            }

            .their-message .message-content {
                background-color: #e9ecef; /* Light gray */
                float: left; /* Push to left */
                color: #333;
            }
            .their-message .message-timestamp {
                text-align: left; /* Timestamp aligned with their message */
            }

            .system-message {
                text-align: center;
                font-style: italic;
                color: #666;
                margin: 15px 0;
            }
        """)
        self.load_contacts_from_db() # Load contacts when UI initializes


    def load_contacts_from_db(self):
        self.contact_list_widget.clear()
        contacts = get_contacts()
        for contact in contacts:
            if contact != self.username: # Don't add self to contact list
                item = QListWidgetItem(contact)
                self.contact_list_widget.addItem(item)
        
        # Select the first contact if available and load its chat
        if self.contact_list_widget.count() > 0:
            self.contact_list_widget.setCurrentRow(0)
            self.load_chat(self.contact_list_widget.currentItem())


    def show_add_contact_dialog(self):
        contact_name, ok = QInputDialog.getText(self, 'Add New Contact', 'Enter username of new contact:')
        if ok and contact_name.strip():
            contact_name = contact_name.strip()
            if contact_name == self.username:
                QMessageBox.warning(self, "Invalid Contact", "Cannot add yourself as a contact.")
                return
            if add_contact(contact_name):
                QMessageBox.information(self, "Success", f"Contact '{contact_name}' added.")
                self.load_contacts_from_db() # Reload to show new contact
            else:
                QMessageBox.warning(self, "Exists", f"Contact '{contact_name}' already exists.")


    def connect_to_server_threaded(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Short timeout for initial connect attempt
            self.client_socket.settimeout(5.0) # 5 seconds timeout for connection
            self.client_socket.connect((HOST, PORT))
            self.client_socket.settimeout(None) # Remove timeout for ongoing communication

            self.client_thread = ClientWorker(self.client_socket, self.username, self.signals)
            self.client_thread.start()
        except socket.timeout:
            self.signals.server_message.emit(f"Connection timed out. Server not responding on {HOST}:{PORT}.")
        except ConnectionRefusedError:
            self.signals.server_message.emit(f"Connection refused. Is the server running on {HOST}:{PORT}?")
        except Exception as e:
            self.signals.server_message.emit(f"Error connecting to server: {e}")

    def on_connected_to_server(self, username):
        self.append_chat(f"Connected to server as '{username}'.", "system")
        if self.current_chat_partner: # Only enable if a chat is already selected
            self.send_button.setDisabled(False)

    def on_disconnected_from_server(self):
        self.append_chat("Disconnected from server.", "system")
        if self.client_thread and self.client_thread.isRunning():
            self.client_thread.stop()
            self.client_thread.wait(100)
        # Safely close socket if it's still open
        if self.client_socket:
            try:
                self.client_socket.close()
            except OSError:
                pass
        self.client_socket = None # Ensure it's None after closing
        self.client_thread = None
        self.send_button.setDisabled(True) # Disable send button on disconnect

    def update_online_users(self, online_users):
        # This function could update indicators next to contact names (e.g., green dot)
        # For simplicity here, we'll just log it.
        # In a more complex UI, you'd iterate through your contact_list_widget and update their status.
        self.append_chat(f"Online users: {', '.join(online_users)}", "system")


    def load_chat(self, item):
        self.current_chat_partner = item.text()
        self.chat_partner_header.setText(self.current_chat_partner)
        self.chat_display.clear() # Clear previous chat
        
        # Check if client_socket exists AND is active before enabling send button
        if self.client_socket and self.client_socket.fileno() != -1: 
            self.send_button.setEnabled(True)
        else:
            self.send_button.setEnabled(False) # Keep disabled if not connected


        messages = get_messages(self.current_chat_partner)
        for msg in messages:
            if msg["is_sent_by_me"]:
                self.append_chat(msg["content"], "self", msg["timestamp"])
            else:
                self.append_chat(msg["content"], "their", msg["timestamp"])
        
        # Scroll to bottom after loading
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.chat_display.setTextCursor(cursor)


    def handle_message_received(self, message_content, sender_username, chat_partner_username_ignored):
        # chat_partner_username_ignored is passed from ClientWorker, but we use sender_username here
        # for saving as the chat_partner, as it's a message *from* them.
        
        # First, save it.
        save_message(sender_username, sender_username, self.username, message_content, False) # It's from sender to me, so is_sent_by_me is False

        # If the currently active chat is with this sender, display it
        if self.current_chat_partner == sender_username:
            self.append_chat(message_content, "their")
        else:
            # Optionally, show a notification or badge on the contact list item
            print(f"New message from {sender_username}: {message_content}")
            # You might want to bold the contact's name in the list widget
            for item_index in range(self.contact_list_widget.count()):
                item = self.contact_list_widget.item(item_index)
                if item.text() == sender_username:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                    # Also bring it to top, for example
                    # self.contact_list_widget.takeItem(item_index)
                    # self.contact_list_widget.insertItem(0, item)
                    break


    def send_message(self):
        msg = self.message_input.text().strip()
        if not msg:
            return

        if not self.current_chat_partner:
            QMessageBox.warning(self, "No Chat Selected", "Please select a contact to send a message to.")
            return

        # Check if the socket is still valid (not closed or broken)
        if not self.client_socket or self.client_socket.fileno() == -1: # fileno() returns -1 for a closed socket
            self.append_chat("Not connected to server. Please check your connection.", "system")
            self.send_button.setDisabled(True) # Ensure button is disabled
            return

        try:
            encrypted_payload, key_seed = encrypt_message(msg)
            compressed_payload, tree = huffman_compress(encrypted_payload)

            # Packet to send to server
            packet_to_server = {
                "type": "chat_message",
                "sender": self.username,
                "recipient": self.current_chat_partner,
                "payload": {
                    "compressed": compressed_payload,
                    "key_seed": key_seed,
                    "huffman_tree": pickle.dumps(tree) # Serialize Huffman tree
                }
            }
            self.client_socket.sendall(pickle.dumps(packet_to_server))
            
            # Save the message to local database
            save_message(self.current_chat_partner, self.username, self.current_chat_partner, msg, True) # sent by me

            self.append_chat(msg, "self") # Display your own message
            self.message_input.clear()
        except OSError as e: # Catch socket errors specifically
            self.append_chat(f"Network error sending message: {e}", "system")
            QMessageBox.critical(self, "Network Error", f"Failed to send message: {e}\nConnection might be lost.")
            self.on_disconnected_from_server() # Treat as disconnect
        except Exception as e:
            self.append_chat(f"Error sending message: {e}", "system")
            QMessageBox.critical(self, "Send Error", f"Failed to send message: {e}")


    def append_chat(self, msg, sender_type, timestamp=None):
        if timestamp is None:
            timestamp = time.strftime("%H:%M") # Get current time if not provided (for new messages)

        # The key change is to ensure each message is a full self-contained block.
        # We use a wrapper div that is always 100% width, and then use float on the inner
        # message-content div to align it left/right.
        if sender_type == "self":
            html_msg = f"""
            <div class="message-wrapper">
                <div class="message-content my-message">
                    {msg}
                    <span class="message-timestamp">{timestamp}</span>
                </div>
            </div>
            """
        elif sender_type == "their":
            html_msg = f"""
            <div class="message-wrapper">
                <div class="message-content their-message">
                    {msg}
                    <span class="message-timestamp">{timestamp}</span>
                </div>
            </div>
            """
        else: # system message
            html_msg = f'<div class="system-message">{msg}</div>'

        self.chat_display.insertHtml(html_msg)
        # Scroll to the bottom
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.chat_display.setTextCursor(cursor)

    def closeEvent(self, event):
        self.close_connections()
        event.accept()

    def close_connections(self):
        if self.client_thread and self.client_thread.isRunning():
            self.client_thread.stop()
            self.client_thread.wait(1000) # Give it time to finish
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