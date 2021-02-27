import requests
import math
import os
import lxml.html
from random import choice
from PyQt5.QtGui import QStandardItem

PROXY_TXT_API = 'https://www.proxyscan.io/api/proxy?type=https&format=txt'
PLATFORM = os.name

def get_proxy():
    proxy = requests.get(PROXY_TXT_API).text
    return proxy.rstrip()

def convert_size(size_bytes):
    # https://stackoverflow.com/a/14822210
    if size_bytes == 0:
        return '0 B'
    size_name = ('B', 'KB', 'MB', 'GB', 'TB')
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return '%s %s' % (s, size_name[i])

def get_link_info(url):
    try:
        r = requests.get(url)
        html = lxml.html.fromstring(r.content)
        name = html.xpath('//td[@class=\'normal\']')[0].text
        size = html.xpath('//td[@class=\'normal\']')[2].text
        return [name, size]
    except:
        return None

def download(worker, payload={'dl_no_ssl': 'on', 'dlinline': 'on'}, downloaded_size = 0):
    if worker.dl_name:
        try:
            downloaded_size = os.path.getsize(worker.dl_directory + '/' + worker.dl_name)
        except FileNotFoundError:
            downloaded_size = 0
    url = worker.link
    i = 1
    while True:
        if worker.stopped or worker.paused:
            return None if not worker.dl_name else worker.dl_name

        worker.signals.update_signal.emit(worker.data, f'Bypassing ({i})', '')

        proxy = get_proxy()
        proxies = {'https': proxy} if PLATFORM == 'nt' else {'https': f'https://{proxy}'}

        try:
            r = requests.post(url, payload, proxies=proxies)
        except:
            # Proxy failed.
            i += 1
        else:
            if worker.stopped or worker.paused:
                return None if not worker.dl_name else worker.dl_name

            worker.signals.update_signal.emit(worker.data, 'Bypassed', '')
            # Proxy worked.
            break

    html = lxml.html.fromstring(r.content)

    if not html.xpath('/html/body/div[4]/div[2]/a'):
        download(worker)
    else:
        old_url = url
        url = html.xpath('/html/body/div[4]/div[2]/a')[0].get('href')
    
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36',
            'Referer': old_url,
            'Range': f'bytes={downloaded_size}-' 
        }

        r = requests.get(url, stream=True, headers=headers)

        if 'Content-Disposition' in r.headers:
            name = r.headers['Content-Disposition'].split('"')[1]

            if worker.dl_name:
                name = worker.dl_name
            elif os.path.exists(f'{worker.dl_directory}/{name}'):
                i = 1
                while os.path.exists(f'{worker.dl_directory}/({i}) {name}'):
                    i += 1
                name = f'({i}) {name}'

            worker.dl_name = name

            if worker.stopped or worker.paused: return name

            with open(worker.dl_directory + '/' + name, 'ab') as f:
                worker.signals.update_signal.emit(worker.data, 'Downloading', '')
                itrcount=1
                chunk_size = 1024
                bytes_read = 0
                for chunk in r.iter_content(chunk_size):
                    itrcount=itrcount+1
                    f.write(chunk)
                    bytes_read += len(chunk)
                    total_per = 100 * (float(bytes_read) + downloaded_size)
                    total_per /= float(r.headers['Content-Length']) + downloaded_size
                    if worker.stopped or worker.paused: return name
                    worker.signals.update_signal.emit(worker.data, 'Downloading', f'{round(total_per, 1)}%')
            worker.signals.update_signal.emit(worker.data, 'Complete', '')
        else:
            download(worker)
    return