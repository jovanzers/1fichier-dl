import sys
import pickle
import os
import PyQt5.sip
from workers import FilterWorker, DownloadWorker
from PyQt5.QtCore import Qt, QThreadPool
from PyQt5.QtGui import QIcon, QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import (QApplication, QMainWindow, QGridLayout,
                             QPushButton, QWidget, QMessageBox,
                             QTableView, QHeaderView, QHBoxLayout,
                             QPlainTextEdit, QVBoxLayout, QAbstractItemView,
                             QAbstractScrollArea, QLabel, QLineEdit,
                             QFileDialog)

# Absolute path
def abs(f):
    return os.path.abspath(os.path.dirname(__file__)) + '/' + f

# Alert
def alert(text):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Warning)
    msg.setWindowTitle('Alert')
    msg.setText(text)
    msg.exec_()

class GuiBehavior:
    def __init__(self, gui):
        self.filter_thread = QThreadPool()
        self.download_thread = QThreadPool()
        self.download_workers = []
        self.gui = gui

        # Load cached downloads
        with open(abs('app/cache'), 'rb') as f:
            try:
                self.cached_downloads = pickle.load(f)
                for download in self.cached_downloads:
                    self.gui.links = download[0]
                    self.add_links_action(True, download[1], download[2], download)
            except EOFError:
                self.cached_downloads = []
                print('No cached downloads.')
        
        # Load settings
        with open(abs('app/settings'), 'rb') as f:
            try:
                self.settings = pickle.load(f)
            except EOFError:
                self.settings = None
                print('No settings found.')

    def check_selection(self):
        selection = []
        for index in self.gui.table.selectionModel().selectedRows():
            selection.append(index.row())
        return selection
    
    def resume_download(self):
        selected_rows = self.check_selection()
        if not selected_rows:
            alert('No rows were selected.')
        else:
            for i in selected_rows:
                if i < len(self.download_workers):
                    self.download_workers[i].resume()

    def stop_download(self):
        selected_rows = self.check_selection()
        if not selected_rows:
            alert('No rows were selected.')
        else:
            for i in selected_rows:
                if i < len(self.download_workers):
                    self.download_workers[i].stop(i)
                    self.download_workers.remove(self.download_workers[i])

    def pause_download(self):
        selected_rows = self.check_selection()
        if not selected_rows:
            alert('No rows were selected.')
        else:
            for i in selected_rows:
                if i < len(self.download_workers):
                    self.download_workers[i].pause()

    def add_links_action(self, state, dl_name = '', password = '', cached_download = ''):
        worker = FilterWorker(self, dl_name, password, cached_download)

        worker.signals.download_signal.connect(self.download_receive_signal)
        worker.signals.alert_signal.connect(alert)
        
        self.filter_thread.start(worker)
    
    def download_receive_signal(self, row, link, append_row = True, dl_name = ''):
        if append_row:
            self.gui.table_model.appendRow(row)

        worker = DownloadWorker(link, self.gui.table_model, row, self.settings, dl_name)
        worker.signals.update_signal.connect(self.update_receive_signal)
        worker.signals.unpause_signal.connect(self.download_receive_signal)

        self.download_thread.start(worker)
        self.download_workers.append(worker)

    def update_receive_signal(self, data, items):
        if data:
            if not PyQt5.sip.isdeleted(data[2]):
                for i in range(len(items)):
                    if items[i]: data[i].setText(items[i])
    
    def dl_directory_action(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.Directory)
        file_dialog.exec_()
        self.gui.dl_directory_input.setText(file_dialog.selectedFiles()[0])

    def save_settings(self):
        with open(abs('app/settings'), 'wb') as f:
            settings = []
            settings.append(self.gui.dl_directory_input.text())
            pickle.dump(settings, f)
            self.settings = settings
        self.gui.settings.hide()
        

    def exit_handler(self):
        active_downloads = []
        for w in self.download_workers:
            download = w.return_data()
            if download: active_downloads.append(download)
        active_downloads.extend(self.cached_downloads)

        with open(abs('app/cache'), 'wb') as f:
            if active_downloads:
                pickle.dump(active_downloads, f)
        
        os._exit(1)

class Gui:
    def __init__(self):
        self.actions = GuiBehavior(self)
        app = QApplication(sys.argv)
        app.setWindowIcon(QIcon(abs('ico.ico')))
        app.setStyle('Fusion')
        app.aboutToQuit.connect(self.actions.exit_handler)
        self.main_win()
        self.add_links_win()
        self.settings_win()
        sys.exit(app.exec_())
    
    def main_win(self):
        self.main = QMainWindow()
        self.main.setWindowTitle('1Fichier Downloader')
        widget = QWidget(self.main)
        self.main.setCentralWidget(widget)

        grid = QGridLayout()
        # Download Button
        download_btn = QPushButton(QIcon(abs('res/download.svg')), ' Add Link(s)')
        download_btn.clicked.connect(lambda: self.add_links.show())

        # Settings Button
        settings_btn = QPushButton(QIcon(abs('res/settings.svg')), ' Settings')
        settings_btn.clicked.connect(lambda: self.settings.show())

        # Table
        self.table = QTableView()
        headers = ['Name', 'Size', 'Status', 'Down Speed', 'Progress', 'Password']
        self.table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContentsOnFirstShow)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().hide()

        self.table_model = QStandardItemModel()
        self.table_model.setHorizontalHeaderLabels(headers)
        self.table.setModel(self.table_model)

        # Append widgets to grid
        grid.addWidget(download_btn, 0, 0)
        grid.addWidget(settings_btn, 0, 1)
        grid.addWidget(self.table, 1, 0, 1, 2)

        # HL: Resume Button
        resume_btn = QPushButton(QIcon(abs('res/resume.svg')), ' Resume')
        resume_btn.clicked.connect(self.actions.resume_download)

        # HL: Pause Button
        pause_btn = QPushButton(QIcon(abs('res/pause.svg')), ' Pause')
        pause_btn.clicked.connect(self.actions.pause_download)

        # HL: Stop Button
        stop_btn = QPushButton(QIcon(abs('res/stop.svg')), ' Remove')
        stop_btn.clicked.connect(self.actions.stop_download)

        # Horizontal Layout
        hbox = QHBoxLayout()
        hbox.addWidget(resume_btn)
        hbox.addWidget(pause_btn)
        hbox.addWidget(stop_btn)

        self.main.setWindowFlags(self.main.windowFlags()
                                & Qt.CustomizeWindowHint)
                                
        grid.addLayout(hbox, 2, 0, 1, 2)
        widget.setLayout(grid)
        self.main.resize(670, 415)
        self.main.show()
    
    def add_links_win(self):
        self.add_links = QMainWindow(self.main)
        self.add_links.setWindowTitle('Add Link(s)')
        widget = QWidget(self.add_links)
        self.add_links.setCentralWidget(widget)

        layout = QVBoxLayout()

        # Text Edit
        self.links = QPlainTextEdit()
        layout.addWidget(self.links)

        # Add Button
        add_btn = QPushButton('Add Link(s)')
        add_btn.clicked.connect(self.actions.add_links_action)
        layout.addWidget(add_btn)

        self.add_links.setMinimumSize(300, 200)
        widget.setLayout(layout)

    def settings_win(self):
        self.settings = QMainWindow(self.main)
        self.settings.setWindowTitle('Settings')
        widget = QWidget(self.settings)
        self.settings.setCentralWidget(widget)

        # Vertical Layout
        vbox = QVBoxLayout()
        dl_directory_label = QLabel('Change download directory:')

        hbox = QHBoxLayout()

        dl_directory_btn = QPushButton('Select..')
        dl_directory_btn.clicked.connect(self.actions.dl_directory_action)

        self.dl_directory_input = QLineEdit()
        if self.actions.settings is not None:
            self.dl_directory_input.setText(self.actions.settings[0])
        self.dl_directory_input.setDisabled(True)

        hbox.addWidget(dl_directory_btn)
        hbox.addWidget(self.dl_directory_input)

        save_settings = QPushButton('Save Settings')
        save_settings.clicked.connect(self.actions.save_settings)

        vbox.addWidget(dl_directory_label)
        vbox.addLayout(hbox)
        vbox.addWidget(save_settings)

        self.add_links.setMinimumSize(300, 200)
        widget.setLayout(vbox)
        self.settings.setFixedSize(340, 85)