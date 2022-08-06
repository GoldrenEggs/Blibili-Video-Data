import csv
import json
import os
import time
from math import ceil
from threading import Thread
from typing import IO, List, Tuple

import py7zr
import requests

VIDEOS_PATH = 'Data/Videos/'
VIDEOS_RAW_PATH = 'Data/Videos.raw/'
VIDEOS_HOUR_PATH = 'Data/VideosHour/'
VIDEOS_HOUR_RAW_PATH = 'Data/VideosHour.raw/'

HEADERS = {
    'Cookie': 'SESSDATA=9bc04939%2C1675269901%2C7f47e%2A81',
    'User-Agent': ''}

EMPTY = '〃'

VIDEO_HEADER = ('date', 'view', 'like', 'coin', 'favorite', 'share', 'danmaku', 'reply',
                'title', 'desc', 'pic')
USER_DATA_HEADER = ('date', 'following', 'follower', 'likes', 'archive', 'article',
                    'sign', 'notice', 'face', 'top_photo')
VIDEOS_DATA_HEADER = ('number', 'bvid', 'aid', 'tid', 'tname', 'title', 'pubdate', 'ctime',
                      'state', 'duration', 'dynamic', 'cid', 'width', 'height', 'is_stein_gate')


def date() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def csv_last_line(fp: IO[str]) -> dict:  # csv文件最末未有效数据
    f_csv = csv.DictReader(fp)
    d = {k: None for k in f_csv.fieldnames}
    for e, line in enumerate(reversed(list(f_csv))):
        for key in line:
            if d[key] in (None, EMPTY):
                d[key] = line[key]
        if EMPTY not in d.values():
            break
    return d


class UP:
    def __init__(self, uid: int, auto_get: bool = True, out_print: bool = True):
        self.mid: int = uid
        self.videos_bvid: List[str] = []
        self.videos: List[Video] = []
        self.date: str = '0000-00-00 00:00:00'
        self.user_data: dict = {}
        self.out_print: bool = out_print

        if auto_get:
            self.get()

    def get(self):
        self.get_videos_bvid()
        self.get_videos()
        self.get_user_data()
        self.date = date()
        return self

    def save(self):
        Thread(target=self.save_videos_raw_data).start()
        Thread(target=self.save_user_date).start()
        Thread(target=self.save_videos_data, ).start()
        return self

    def get_videos_bvid(self):
        if self.out_print:
            print(f'[{date()}] 正在抓取视频列表')
        videos_bvid = []
        r = requests.get('http://api.bilibili.com/x/space/arc/search', params={'mid': self.mid})
        page_number = ceil(r.json()['data']['page']['count'] / r.json()['data']['page']['ps'])
        for page in range(1, page_number + 1):
            r = requests.get('http://api.bilibili.com/x/space/arc/search', params={'mid': self.mid, 'pn': page})
            video_list = r.json()['data']['list']['vlist']
            for i in range(len(video_list)):
                videos_bvid.append(video_list[i]['bvid'])
        self.videos_bvid = videos_bvid
        print(f'[{date()}] 已取得视频列表：', *videos_bvid)
        return self

    def get_videos(self):
        videos = []
        for bvid in self.videos_bvid:
            videos.append(Video(bvid))
        self.videos = videos
        return self

    def get_user_data(self):
        if self.out_print:
            print(f'[{date()}] 正在抓取用户数据', end='')
        user_data = {'date': date()[:10], 'following': None, 'follower': None, 'likes': None, 'archive': None,
                     'article': None, 'sign': None, 'notice': None, 'face': None, 'top_photo': None}
        r = requests.get('http://api.bilibili.com/x/relation/stat',
                         params={'vmid': self.mid}).json()['data']
        user_data['following'] = r['following']
        user_data['follower'] = r['follower']
        r = requests.get('http://api.bilibili.com/x/space/upstat',
                         params={'mid': self.mid}, headers=HEADERS).json()['data']
        user_data['likes'] = r['likes']
        user_data['archive'] = r['archive']['view']
        user_data['article'] = r['article']['view']
        r = requests.get('http://api.bilibili.com/x/space/acc/info',
                         params={'mid': self.mid}, headers=HEADERS).json()['data']
        user_data['sign'] = r['sign']
        user_data['face'] = r['face']
        user_data['top_photo'] = r['top_photo']
        r = requests.get('http://api.bilibili.com/x/space/notice',
                         params={'mid': self.mid}).json()['data']
        user_data['notice'] = r
        self.user_data = user_data
        if self.out_print:
            print(f'  完成')
        return self

    def save_videos_raw_data(self):
        if self.out_print:
            print(f'[{date()}] 正在保存视频原始数据')
        raw_data = []
        for video in self.videos:
            raw_data.append(video.data)
        with open(VIDEOS_RAW_PATH + self.date[:10] + '.json', 'w+', encoding='utf-8') as f:
            json.dump(raw_data, f, ensure_ascii=False)
        if self.out_print:
            print(f'[{date()}] 正在压缩视频原始数据')
        archive = py7zr.SevenZipFile(f'{VIDEOS_RAW_PATH}{self.date[:10]}.7z', 'w')
        archive.write(f'{VIDEOS_RAW_PATH}{self.date[:10]}.json', arcname=f'{self.date[:10]}.json')
        archive.close()
        os.remove(f'{VIDEOS_RAW_PATH}{self.date[:10]}.json')
        return self

    def save_videos_data(self):
        if self.out_print:
            print(f'[{date()}] 正在保存视频数据')
        for video in self.videos:
            video.save()
        return self

    def save_user_date(self):
        if self.out_print:
            print(f'[{date()}] 正在保存用户数据')
        try:
            f = open('Data/UserData.csv', 'r+', encoding='utf-8', newline='')
            f_csv = csv.DictWriter(f, USER_DATA_HEADER)
            last_line = csv_last_line(f)
            for i in USER_DATA_HEADER[6:9]:
                if self.user_data[i] == last_line[i]:
                    self.user_data[i] = EMPTY
            if self.user_data[USER_DATA_HEADER[9]][16:] == last_line[USER_DATA_HEADER[9]][16:]:
                self.user_data[USER_DATA_HEADER[9]] = EMPTY
            f_csv.writerow(self.user_data)
        except FileNotFoundError:
            f = open('Data/UserData.csv', 'w', encoding='utf-8-sig', newline='')
            f_csv = csv.DictWriter(f, USER_DATA_HEADER)
            f_csv.writeheader()
            f_csv.writerow(self.user_data)
        return self

    def get_and_save_hour(self, day: int = 14):
        new_videos: Tuple[Video] = self.check_new_videos(day)
        for video in new_videos:
            video.get().save(is_hour=True)
        return self

    def check_update(self, check_video_count: int = 5, auto_update_videos_data: bool = True) -> tuple:
        req = requests.get('http://api.bilibili.com/x/space/arc/search',
                           params={'mid': self.mid, 'ps': check_video_count})
        check_videos_bvid = [data['bvid'] for data in req.json()['data']['list']['vlist']]
        videos_bvid = []
        new_videos_bvid = []
        with open('Data/VideosData.csv', 'r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                videos_bvid.append(row['bvid'])
        for check_video_bvid in check_videos_bvid:
            if check_video_bvid not in videos_bvid:
                new_videos_bvid.append(check_video_bvid)
        if auto_update_videos_data:
            for bvid in reversed(new_videos_bvid):
                self.update_videos_data(bvid)
                Abbreviations.add(bvid)
        return tuple(reversed(new_videos_bvid))

    def update_videos_data(self, bvid: str):  # 更新VideosData.csv，带有重复添加识别（不太可靠，因为只检测最后一行）
        video_data = requests.get('http://api.bilibili.com/x/web-interface/view', params={'bvid': bvid}).json()['data']
        f_videos_data = open('Data/VideosData.csv', 'a', encoding='utf-8-sig', newline='')
        f_csv = csv.DictWriter(f_videos_data, VIDEOS_DATA_HEADER)
        *_, last_line = csv.DictReader(open('Data/VideosData.csv', 'r', encoding='utf-8-sig'))
        if last_line['bvid'] == bvid:
            f_videos_data.close()
            return self
        d = {'number': int(last_line['number']) + 1}
        for i in VIDEOS_DATA_HEADER[1:12]:
            d[i] = video_data[i]
        d['pubdate'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(d['pubdate']))
        d['ctime'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(d['ctime']))
        d['width'] = video_data['dimension']['width']
        d['height'] = video_data['dimension']['height']
        d['is_stein_gate'] = video_data['rights']['is_stein_gate']
        f_csv.writerow(d)
        f_videos_data.close()

    def check_new_videos(self, day: int = 14):  # 返回在day天数内更新的视频实例
        new_videos: List[Video] = []
        new_videos_bvid = self.check_new_videos_bvid(day)
        for video in self.videos:
            if video.bvid in new_videos_bvid:
                new_videos.append(video)
        if self.out_print:
            print(f'[{date()}] 已找到视频：', *[Abbreviations[bvid] for bvid in new_videos_bvid])
        return tuple(reversed(new_videos))

    def check_new_videos_bvid(self, day: int):  # 返回打在day天内更新的视频BV号
        if self.out_print:
            print(f'[{date()}] 正在查找{day}天内更新的视频')
        new_videos_bvid: List[str] = []
        now = time.time()
        f_csv = csv.DictReader(open('Data/VideosData.csv', 'r', encoding='utf-8-sig'))
        for row in f_csv:
            pubdate = time.mktime(time.strptime(row['pubdate'], '%Y-%m-%d %H:%M:%S'))
            if now - pubdate <= 86400 * day:
                new_videos_bvid.append(row['bvid'])
        return tuple(new_videos_bvid)


class Video:
    def __init__(self, bvid: str, out_print: bool = True):
        self.bvid: str = bvid
        self.date: str = '0000-00-00 00:00:00'
        self.data: dict = {}
        self.out_print: bool = out_print

        self.get()

    def get(self):
        if self.out_print:
            print(f'[{date()}] 正在抓取：{self.bvid}', end='')
        req = requests.get('http://api.bilibili.com/x/web-interface/view',
                           params={'bvid': self.bvid}).json()
        if req['code'] == 0:
            self.data = req['data']
            self.date = date()
            print('  成功')
        else:
            print('  失败 ' + str(req))
        return self

    def save(self, is_hour: bool = False):
        if self.out_print:
            print('[{0}] 正在保存：[{1}] {2}.csv'
                  .format(date(), Abbreviations[self.bvid], self.bvid))
        d = {'date': self.date[:10] if not is_hour else self.date}
        for i in VIDEO_HEADER[1:8]:
            d[i] = self.data['stat'][i]
        for i in VIDEO_HEADER[8:]:
            d[i] = self.data[i]
        if not is_hour:
            path = f'{VIDEOS_PATH}[{Abbreviations[self.bvid]}] {self.bvid}.csv'
        else:
            path = f'{VIDEOS_HOUR_PATH}/[{Abbreviations[self.bvid]}] {self.bvid}.csv'
        try:
            f = open(path, 'r+', encoding='utf-8', newline='')
            f_csv = csv.DictWriter(f, VIDEO_HEADER)
            last_line = csv_last_line(f)
            for i in VIDEO_HEADER[8:]:
                if d[i] == last_line[i]:
                    d[i] = EMPTY
            f_csv.writerow(d)
        except FileNotFoundError:
            f = open(path, 'w', encoding='utf-8-sig', newline='')
            f_csv = csv.DictWriter(f, VIDEO_HEADER)
            f_csv.writeheader()
            f_csv.writerow(d)
        f.close()
        if is_hour:
            self.save_hour_raw()
        return self

    def save_hour_raw(self):
        file_name = f'[{Abbreviations[self.bvid]}] {self.bvid}'
        with open(f'{VIDEOS_HOUR_RAW_PATH}{file_name}.json', 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False)
        try:
            archive = py7zr.SevenZipFile(f'{VIDEOS_HOUR_RAW_PATH}{file_name}.7z', 'a')
        except FileNotFoundError:
            archive = py7zr.SevenZipFile(f'{VIDEOS_HOUR_RAW_PATH}{file_name}.7z', 'w')
        archive.write(f'{VIDEOS_HOUR_RAW_PATH}{file_name}.json', arcname=f'{self.date}.json')
        archive.close()
        os.remove(f'{VIDEOS_HOUR_RAW_PATH}{file_name}.json')


class Abbreviations:
    abbreviations: dict = json.load(f_abbreviations := open('Data/Abbreviations.json', 'r', encoding='utf-8'))
    f_abbreviations.close()

    def __class_getitem__(cls, item):
        if item[:2] == 'BV':
            return cls.abbreviations[item]
        else:
            for k, v in cls.abbreviations.items():
                if v == item:
                    return k

    @classmethod
    def rename(cls, bvid: str = '', name: str = ''):
        confirm = 'Y'
        if bvid == '':
            bvid = input('\n请输入BV号：')
        if bvid not in cls.abbreviations.keys():
            print('该BV号不存在。')
            return
        if name == '':
            name = input(f'当前简称：【{cls[bvid]}】\n请输新入简称：')
            confirm = input(f'确认将{bvid}：【{cls[bvid]}】 修改为 【{name}】 吗？(Y/N)')
        if confirm in ('Y', 'y', 'yes'):
            src = f'{VIDEOS_PATH}[{cls[bvid]}] {bvid}.csv'
            dst = f'{VIDEOS_PATH}[{name}] {bvid}.csv'
            src_hour = f'{VIDEOS_HOUR_PATH}[{cls[bvid]}] {bvid}.csv'
            dst_hour = f'{VIDEOS_HOUR_PATH}[{name}] {bvid}.csv'
            src_hour_raw = f'{VIDEOS_HOUR_RAW_PATH}[{cls[bvid]}] {bvid}.7z'
            dst_hour_raw = f'{VIDEOS_HOUR_RAW_PATH}[{name}] {bvid}.7z'
            os.rename(src, dst)
            os.rename(src_hour, dst_hour)
            os.rename(src_hour_raw, dst_hour_raw)
            cls.abbreviations[bvid] = name
            with open('Data/Abbreviations.json', 'w', encoding='utf-8') as f:
                json.dump(cls.abbreviations, f, ensure_ascii=False, indent=4)

    @classmethod
    def add(cls, bvid: str):
        name = '错误'
        for row in csv.DictReader(open(f'Data/VideosData.csv', 'r', encoding='utf-8-sig')):
            if row['bvid'] == bvid:
                name = row['title'][:6]
        cls.abbreviations[bvid] = name
        d = {bvid: name}
        d.update(cls.abbreviations)
        cls.abbreviations = d
        with open('Data/Abbreviations.json', 'w', encoding='utf-8') as f:
            json.dump(cls.abbreviations, f, ensure_ascii=False, indent=4)

    @classmethod
    def test(cls):
        print(type(cls.abbreviations))


if __name__ == '__main__':
    goldeneggs = UP(13337125)
    goldeneggs.save()
