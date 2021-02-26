import json, requests

x = requests.get('https://1fichier.com/dir/C5DLdJgN?json=1')
x = x.json()

for d in x:
    print(d['link'])
    print(int(d['size']))