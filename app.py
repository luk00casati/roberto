from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QScrollArea, QPushButton, QLineEdit, QHBoxLayout, QStackedWidget
import sys
import os
import sqlite3
import random
import string
import pyperclip
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Hash import SHA256

# LEGENDA
# main -> 0
# add_frame -> 1
# asking_frame -> 2
# creating_master -> 3
# insert_master -> 4

master_pass = "null"
master_pass_encoded = str.encode(master_pass)

fix_salt = b"dC\x9aR\xec\xb3\x8dr\xc4M\\\x8e\x9b\xa9\x1fLS\xe9m +\xbb\x10\xbf\xb7x\xdd\xeb3-'\xb1"

master_key = PBKDF2(master_pass_encoded, fix_salt, dkLen=32)

user_name = os.getlogin()

def generatepassword(length=15, options={}):
    chars = []
    
    if not options.get('skip_lower_case', False):
        chars.extend(string.ascii_lowercase)
    
    if not options.get('skip_upper_case', False):
        chars.extend(string.ascii_uppercase)
    
    if not options.get('skip_numbers', False):
        chars.extend(string.digits)
    
    if not options.get('skip_symbols', False):
        chars.extend('!@#$%^&(){}[]-_<>?')
    
    if not options.get('dont_exclude_unfrieldly_chars', False):
        chars = [c for c in chars if c not in 'iIoO01l!']
    
    if options.get('skip_url_unsafe', False):
        chars = [c for c in chars if c not in '$&+/,;=?@<>#%{}|^~[]`']
    
    password = ''.join(random.choice(chars) for _ in range(length))
    
    return password

class Element(QWidget):
    def __init__(self, main_instance, name, cipher_pass, iv_pass):
        super().__init__()
        self.main_instance = main_instance
        self.password_visible = False
        self.cipher_pass = cipher_pass
        self.iv_pass = iv_pass
        #decript
        cipher_pass_byte = bytes.fromhex(cipher_pass)
        iv_pass_byte = bytes.fromhex(iv_pass)
        cipher = AES.new(master_key, AES.MODE_CBC, iv_pass_byte)
        decrypt_byte = unpad(cipher.decrypt(cipher_pass_byte), AES.block_size)
        self.clear_password = decrypt_byte.decode('UTF-8')
        self.hide_password = "***************"

        self.Name = QLabel(name, self)
        self.Password = QLabel(self.hide_password, self)
        self.Delete = QPushButton("Delete", self)
        self.Show = QPushButton("Show", self)
        self.Copy = QPushButton("Copy", self)

        self.Delete.clicked.connect(self.delete_button)
        self.Copy.clicked.connect(self.copy_to_clipboard)
        self.Show.clicked.connect(self.toggle_password_visibility)

        layout = QHBoxLayout(self)
        layout.addWidget(self.Name)
        layout.addWidget(self.Password)
        layout.addWidget(self.Delete)
        layout.addWidget(self.Show)
        layout.addWidget(self.Copy)

        self.setLayout(layout)

    def copy_to_clipboard(self):
        pyperclip.copy(self.clear_password)

    def delete_button(self):
        self.deleteLater()
        self.main_instance.show_asking_screen(self.Name.text())

    def toggle_password_visibility(self):
        self.password_visible = not self.password_visible
        if self.password_visible:
            self.Password.setText(self.clear_password)
            self.Show.setText("Hide")
        else:
            self.Password.setText(self.hide_password)
            self.Show.setText("Show")


class DatabaseHandler:
    def __init__(self, db_name="test.db"):
        with sqlite3.connect(db_name) as conn:
            self.cursor = conn.cursor()

            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS password_db (
                    name VARCHAR(255) UNIQUE NOT NULL,
                    cipher_pass VARCHAR(255) NOT NULL,
                    iv_pass VARCHAR(255) NOT NULL 
                )''')

            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS master_hash (
                    hash VARCHAR(255) NOT NULL
                )''')

            conn.commit()

    def execute_query(self, query, parameters=None):
        try:
            if parameters:
                self.cursor.execute(query, parameters)
            else:
                self.cursor.execute(query)
            self.cursor.connection.commit()
        except sqlite3.Error as e:
            print(f"Error executing query '{query}': {e}")

    def fetch_all(self, query, parameters=None):
        try:
            if parameters:
                self.cursor.execute(query, parameters)
            else:
                self.cursor.execute(query)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error fetching data for query '{query}': {e}")
            return []

    def is_name_unique(self, name):
        query = 'SELECT COUNT(*) FROM password_db WHERE name = ?'
        parameters = (name,)
        count = self.fetch_all(query, parameters)[0][0]
        return count == 0

    def add_password(self, name, cipher_pass, iv_pass):
        query = 'INSERT INTO password_db (name, cipher_pass, iv_pass) VALUES (?, ?, ?)'
        parameters = (name, cipher_pass, iv_pass)
        self.execute_query(query, parameters)

    def delete_password(self, name):
        query = 'DELETE FROM password_db WHERE name = ?'
        parameters = (name,)
        self.execute_query(query, parameters)

    def insert_hash(self, v_hash):
        query = 'INSERT INTO master_hash (hash) VALUES (?)';
        parameters = (v_hash)
        self.execute_query(query, parameters)

    def __del__(self):
        self.cursor.connection.close()



class Main(QWidget):
    def __init__(self):
        super().__init__()

        self.db_handler = DatabaseHandler()
        self.stacked_widget = QStackedWidget(self)
        self.setup_main_screen()
        self.setup_add_screen()

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.stacked_widget)

    def setup_main_screen(self):
        main_screen = QWidget(self)
        layout = QVBoxLayout(main_screen)

        layout_bar = QHBoxLayout()
        self.add_button_bar = QPushButton("Add", main_screen)
        self.option_bar = QPushButton("Option", main_screen)
        self.text_input_bar = QLineEdit(main_screen)
        self.search_bar = QPushButton("Search", main_screen)

        layout_bar.addWidget(self.add_button_bar)
        layout_bar.addWidget(self.option_bar)
        layout_bar.addWidget(self.text_input_bar)
        layout_bar.addWidget(self.search_bar)

        layout.addLayout(layout_bar)

        self.scroller = QScrollArea(main_screen)
        self.scroll_content = QWidget(self.scroller)
        self.scroll_layout = QVBoxLayout(self.scroll_content)

        self.scroller.setWidgetResizable(True)
        self.scroller.setWidget(self.scroll_content)
        self.update_elements()

        layout.addWidget(self.scroller)

        self.add_button_bar.clicked.connect(self.show_add_screen)
        self.search_bar.clicked.connect(self.update_elements)
        self.stacked_widget.addWidget(main_screen)

    def update_elements(self):
        if not self.text_input_bar.text():
            self.clear_layout(self.scroll_layout)

            db_handler = DatabaseHandler()
            elements_data = db_handler.fetch_all('SELECT name, cipher_pass, iv_pass FROM password_db')

            for name, cipher_pass, iv_pass in elements_data:
                element = Element(self, name, cipher_pass, iv_pass)
                self.scroll_layout.addWidget(element)

            self.scroll_content.setLayout(self.scroll_layout)

        elif self.text_input_bar.text():
            self.clear_layout(self.scroll_layout)
            search_phrase = f"%{self.text_input_bar.text()}%"

            db_handler = DatabaseHandler()
            elements_data = db_handler.fetch_all('SELECT name FROM password_db WHERE name LIKE ?', (search_phrase,))

            for name, password in elements_data:
                element = Element(self, name, password)
                self.scroll_layout.addWidget(element)

            self.scroll_content.setLayout(self.scroll_layout)

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

    def setup_add_screen(self):
        add_screen = QWidget(self)
        layout = QVBoxLayout(add_screen)

        self.add_button_frame = QPushButton("Add", add_screen)
        self.back = QPushButton("Back", add_screen)
        self.name_label = QLabel("Name:", add_screen)
        self.name_line = QLineEdit(add_screen)
        self.password_label = QLabel("Password:", add_screen)
        self.password_line = QLineEdit(add_screen)
        self.rand_gen_button = QPushButton("random gen", add_screen)
        self.error_label = QLabel("Error", add_screen)
        self.error_label.hide()

        layout.addWidget(self.name_label)
        layout.addWidget(self.name_line)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_line)
        layout.addWidget(self.rand_gen_button)
        layout.addWidget(self.add_button_frame)
        layout.addWidget(self.back)
        layout.addWidget(self.error_label)

        self.add_button_frame.clicked.connect(self.add_screen_button)
        self.rand_gen_button.clicked.connect(self.gen_password)
        self.back.clicked.connect(self.show_main_screen)
        self.stacked_widget.addWidget(add_screen)

    def gen_password(self):
        self.password_line.setText(generatepassword())

    def is_name_unique(self, name):
        return self.db_handler.is_name_unique(name)

    def add_screen_button(self):
        name = self.name_line.text()
        password_clear = self.password_line.text()

        if name and password_clear:
            if self.is_name_unique(name):
                password_clear_encoded = str.encode(password_clear)
                #cript
                cipher = AES.new(master_key, AES.MODE_CBC)
                cipher_data = cipher.encrypt(pad(password_clear_encoded, AES.block_size))
                cipherhex = cipher_data.hex()
                iv = cipher.iv
                ivhex = iv.hex()

                self.db_handler.add_password(name, cipherhex, ivhex)
                self.name_line.clear()
                self.password_line.clear()
                self.update_elements()
                self.stacked_widget.setCurrentIndex(0)
                self.error_label.hide()
            else:
                self.error_label.setText("Name already exists. Please choose a different name.")
                self.error_label.show()
        else:
            self.error_label.setText("Name and password cannot be empty.")
            self.error_label.show()

    def show_add_screen(self):
        self.error_label.hide()
        self.stacked_widget.setCurrentIndex(1)

    def show_main_screen(self):
        self.update_elements()
        self.stacked_widget.setCurrentIndex(0)

    def show_asking_screen(self, name):
        self.setup_asking_screen(name)
        self.stacked_widget.setCurrentIndex(2)

    def show_create_master_password(self):
        self.stacked_widget.setCurrentIndex(3)

    def setup_asking_screen(self, name):
        asking_screen = QWidget(self)
        self.pass_name = name
        layout = QVBoxLayout(asking_screen)

        self.asking_label = QLabel(f"want you delete {name}?")
        self.yes_button = QPushButton("yes", asking_screen)
        self.no_button = QPushButton("no", asking_screen)

        layout.addWidget(self.asking_label)
        layout.addWidget(self.yes_button)
        layout.addWidget(self.no_button)
        self.setLayout(layout)
        self.stacked_widget.addWidget(asking_screen)

        self.no_button.clicked.connect(self.no_element_delete)
        self.yes_button.clicked.connect(self.yes_element_delete)

    def yes_element_delete(self):
        db_handler = DatabaseHandler()
        db_handler.delete_password(self.pass_name)
        self.show_main_screen()

    def no_element_delete(self):
        self.show_main_screen()

    def setup_create_master_password(self):
        create_master = QWidget(self)
        layout = QVBoxLayout(create_master)

        self.label_create_master = QLabel("choose a master master_password:", create_master)
        self.line_create_master1 = QLineEdit(create_master)
        self.line_create_master2 = QLineEdit(create_master)
        self.button_create_master = QPushButton("enter", create_master)
        self.error_label_create_master = QLabel("error", create_master)
        self.error_label_create_master.hide()

        layout.addWidget(self.label_create_master)
        layout.addWidget(self.line_create_master1)
        layout.addWidget(self.line_create_master2)
        layout.addWidget(self.button_create_master)
        layout.addWidget(self.error_label_create_master)

        self.stacked_widget.addWidget(create_master)
        self.button_create_master.clicked.connect(self.enter_button_create_master)

    def enter_button_create_master(self):
        if self.line_create_master1.text() and self.line_create_master2.text() and self.line_create_master1.text() == self.line_create_master2.text():
            global master_pass
            master_pass = self.line_create_master1.text()
            line_encoded = self.line_create_master1.text().str.endcode()
            hash256 = SHA256.new(line_encoded)
            hexhash256_hash = hash256.hexdigest()
            db_handler = DatabaseHandler()
            db_handler.insert_hash(hexhash256_hash)
            self.show_main_screen()
        else:
            self.error_label_create_master.show()

if __name__ == "__main__":
    app = QApplication()
    win = Main()
    win.show()
    sys.exit(app.exec())
