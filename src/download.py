import requests
import math
import os
import lxml.html
from random import choice
from PyQt5.QtGui import QStandardItem

PROXY_TXT_API = 'https://www.proxyscan.io/api/proxy?type=https&format=txt'

def get_proxy():
    proxy = requests.get(PROXY_TXT_API).text
    return proxy.rstrip()

def get_link_info(url):
    try:
        r = requests.get(url)
        html = lxml.html.fromstring(r.content)
        name = html.xpath('//td[@class=\'normal\']')[0].text
        size = html.xpath('//td[@class=\'normal\']')[2].text
        return [name, size]
    except:
        return None

def download(worker, payload={'dl_no_ssl': 'on', 'dlinline': 'on'}):
    if worker.dl_name:
        downloaded_size = os.path.getsize(os.path.abspath(os.path.dirname(__file__)) + '/' + worker.dl_name)
    else:
        downloaded_size = 0
    url = worker.link
    i = 1
    while True:
        if not worker.data: return None
        if worker.paused: return None
        worker.signals.update_signal.emit(worker.data, f'Bypassing ({i})', '')
        
        proxy = get_proxy()
        proxies = {'https': proxy}
        try:
            r = requests.post(url, payload, proxies=proxies)
        except:
            # Proxy failed.
            i += 1
            pass
        else:
            if not worker.data: return None
            if worker.paused: return None
            worker.signals.update_signal.emit(worker.data, 'Bypassed', '')
            # Proxy worked.
            break

    html = lxml.html.fromstring(r.content)

    try:
        old_url = url
        url = html.xpath('/html/body/div[4]/div[2]/a')[0].get('href')
    except:
        download(worker)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36',
        'Referer': old_url,
        'Range': f'bytes={downloaded_size}-' 
    }

    r = requests.get(url, stream=True, headers=headers)

    try:
        name = r.headers['Content-Disposition'].split('"')[1]
    except:
        download(worker)

    if os.path.exists(name) and not worker.dl_name:
        i = 1
        while os.path.exists(f'({i}) {name}'):
            i += 1
        name = f'({i}) {name}'
        
    if not worker.data: return name
    if worker.paused: return name
    with open(name, 'ab') as f:
        worker.signals.update_signal.emit(worker.data, 'Downloading', '')
        itrcount=1
        chunk_size = 1024
        bytes_read = 0
        for chunk in r.iter_content(chunk_size):
            itrcount=itrcount+1
            f.write(chunk)
            bytes_read += len(chunk)
            total_per = 100 * (float(bytes_read) + downloaded_size)
            total_per /= float(r.headers['Content-Length'])
            if not worker.data: return name
            if worker.paused: return name
            worker.signals.update_signal.emit(worker.data, 'Downloading', f'{round(total_per, 1)}%')