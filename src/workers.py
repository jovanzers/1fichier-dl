import os
from download import *
from PyQt5.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QStandardItem

class WorkerSignals(QObject):
    download_signal = pyqtSignal(list, str, bool, str)
    alert_signal = pyqtSignal(str)
    update_signal = pyqtSignal(list, str, str)
    unpause_signal = pyqtSignal(list, str, bool, str)

class Filter_Worker(QRunnable):
    def __init__(self, links, dl_name = ''):
        super(Filter_Worker, self).__init__()
        self.links = links
        self.signals = WorkerSignals()
        self.dl_name = dl_name
        self.percentage = 0

    @pyqtSlot()
    def run(self):
        self.valid_links = []

        if isinstance(self.links, str):
            self.valid_links = [self.links]
            self.percentage = '-'
        else:
            links = self.links.toPlainText().splitlines()

            for link in links:
                link = link.strip()
                if '1fichier.com/' in link:
                    if not 'https://' in link[0:8] and not 'http://' in link[0:7]:
                        link = f'https://{link}'
                    if '&af=' in link:
                        link = link.split('&af=')[0]
                    self.valid_links.append(link)

            if not self.valid_links:
                self.signals.alert_signal.emit('The link(s) you inserted were not valid.')

        for link in self.valid_links:
            if '/dir/' in link:
                folder = requests.get(f'{link}?json=1')
                folder = folder.json()
                for f in folder:
                    link = f['link']
                    info = [f['filename'], convert_size(int(f['size']))]
                    row = []
                    for val in info:
                        data = QStandardItem(val)
                        row.append(data)
                    row.extend([QStandardItem('Added'), QStandardItem(f'{self.percentage}%')])
                    self.signals.download_signal.emit(row, link, True, self.dl_name)
            else:
                info = get_link_info(link)
                if info is not None:
                    row = []
                    for val in info:
                        data = QStandardItem(val)
                        row.append(data)
                    row.extend([QStandardItem('Added'), QStandardItem(f'{self.percentage}%')])
                    self.signals.download_signal.emit(row, link, True, self.dl_name)

class Download_Worker(QRunnable):
    def __init__(self, link, table_model, data, settings, dl_name = ''):
        super(Download_Worker, self).__init__()
        self.link = link
        self.table_model = table_model
        self.data = data
        self.signals = WorkerSignals()
        self.paused = self.stopped = self.complete = False
        self.dl_name = dl_name
        self.dl_directory = settings[0] if settings is not None else os.path.abspath(os.path.dirname(__file__))

    @pyqtSlot()
    def run(self):
        dl_name = download(self)
        self.dl_name = dl_name

        if dl_name and self.stopped:
            os.remove(dl_name)

        if self.paused:
            self.signals.update_signal.emit(self.data, 'Paused', '')
        else:
            if not dl_name:
                self.complete = True

    def stop(self, i):
        self.table_model.removeRow(i)
        self.stopped = True
    
    def pause(self):
        if not self.complete:
            self.paused = True

    def resume(self):
        if self.paused == True:
            self.paused = False
            self.signals.unpause_signal.emit(self.data, self.link, False, self.dl_name)
    
    def return_data(self):
        if not self.stopped and not self.complete:
            data = []
            data.append(self.link)
            if self.dl_name: 
                data.append(self.dl_name)
            else:
                data.append(None)
            return data