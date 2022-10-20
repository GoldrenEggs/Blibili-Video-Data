import yaml

import requests

with open('config.yaml', 'r', encoding='utf-8') as f:
    HEADERS = yaml.safe_load(f)['Headers']

MID = 13337125

r = requests.get('https://api.bilibili.com/x/space/upstat',
                 params={'mid': MID}, headers=HEADERS).json()
# r = requests.get('http://api.bilibili.com/x/space/acc/info',
#                  params={'mid': MID}, headers=HEADERS).json()
print(r)
