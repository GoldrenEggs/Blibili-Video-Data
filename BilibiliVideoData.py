import json
import csv
import os
import time
from math import ceil
from typing import IO, List
from sys import getsizeof

import requests

headers = {
    'Cookie': 'SESSDATA=dda84cce%2C1659684550%2C5a52b%2A21',
    'User-Agent': ''
}

EMPTY = '〃'

VIDEO_HEADER = ('date', 'view', 'like', 'coin', 'favorite', 'share', 'danmaku', 'reply',
                'title', 'desc', 'pic')
USER_DATA_HEADER = ('date', 'following', 'follower', 'likes', 'archive', 'article',
                    'sign', 'notice', 'face', 'top_photo')


class Abbreviations:
    abbreviations: dict = json.load(f_abbreviations := open('Data/Abbreviations.json', 'r', encoding='utf-8'))
    f_abbreviations.close()
    reverse = {k: v for v, k in abbreviations.items()}

    def __class_getitem__(cls, item):
        if item[:2] == 'BV':
            return cls.abbreviations[item]
        else:
            return cls.reverse[item]

    @classmethod
    def change_name(cls, bvid: str, name: str):
        cls.abbreviations[bvid] = name
        with open('Data/Abbreviations.json', 'w', encoding='utf-8') as f:
            json.dump(cls.abbreviations, f, indent=4)

    @classmethod
    def add(cls, bvid: str, name: str):
        cls.abbreviations[bvid] = name
        d = {bvid: name}
        cls.abbreviations = d.update(cls.abbreviations)
        with open('Data/Abbreviations.json', 'w', encoding='utf-8') as f:
            json.dump(cls.abbreviations, f, indent=4)
        cls.reverse = {k: v for v, k in cls.abbreviations.items()}


def date(accuracy: str) -> str:
    if accuracy == 'day':
        return time.strftime("%Y-%m-%d", time.localtime())
    elif accuracy == 's':
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    else:
        raise Exception('日期精度类型错误')


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
    def __init__(self, uid: int, out_print: bool = True):
        self.mid: int = uid
        self.videos_bvid: List[str] = []
        self.videos: List[Video] = []
        self.user_data: dict = {}
        self.date = '0000-00-00'
        self.out_print: bool = out_print

        self.get_data()

    def get_data(self, week: bool = False):
        self.get_videos_bvid()
        self.get_videos()
        self.get_user_data()
        self.date = date('s') if week else date('day')

    def get_videos_bvid(self):
        if self.out_print:
            print(f'[{date("s")}] 正在抓取视频列表')
        videos_bvid = []
        r = requests.get('http://api.bilibili.com/x/space/arc/search', params={'mid': self.mid})
        page_number = ceil(r.json()['data']['page']['count'] / r.json()['data']['page']['ps'])
        for page in range(1, page_number + 1):
            r = requests.get('http://api.bilibili.com/x/space/arc/search', params={'mid': self.mid, 'pn': page})
            video_list = r.json()['data']['list']['vlist']
            for i in range(len(video_list)):
                videos_bvid.append(video_list[i]['bvid'])
        self.videos_bvid = videos_bvid
        print(f'[{date("s")}] 已取得视频列表：', *videos_bvid)
        return self

    def get_videos(self):
        videos = []
        for bvid in self.videos_bvid:
            videos.append(Video(bvid))
        self.videos = videos
        return self

    def get_user_data(self):
        if self.out_print:
            print(f'[{date("s")}] 正在抓取用户数据')
        user_data = {'date': date('day'), 'following': None, 'follower': None, 'likes': None, 'archive': None,
                     'article': None, 'sign': None, 'notice': None, 'face': None, 'top_photo': None}
        r = requests.get('http://api.bilibili.com/x/relation/stat',
                         params={'vmid': self.mid}).json()['data']
        user_data['following'] = r['following']
        user_data['follower'] = r['follower']
        r = requests.get('http://api.bilibili.com/x/space/upstat',
                         params={'mid': self.mid}, headers=headers).json()['data']
        user_data['likes'] = r['likes']
        user_data['archive'] = r['archive']['view']
        user_data['article'] = r['article']['view']
        r = requests.get('http://api.bilibili.com/x/space/acc/info',
                         params={'mid': self.mid}, headers=headers).json()['data']
        user_data['sign'] = r['sign']
        user_data['face'] = r['face']
        user_data['top_photo'] = r['top_photo']
        r = requests.get('http://api.bilibili.com/x/space/notice',
                         params={'mid': self.mid}).json()['data']
        user_data['notice'] = r
        self.user_data = user_data
        return self

    def save(self, week: bool = False):
        raw_data = []
        for video in self.videos:
            raw_data.append(video.data)
            video.save(week)
        if not week:
            print(f'[{date("s")}] 正在保存原始数据')
            with open('Data/VideosRaw/' + date('day') + '.json', 'w+', encoding='utf-8') as f:
                json.dump(raw_data, f, ensure_ascii=False)
            self.save_user_date()
        return self

    def save_user_date(self):
        if self.out_print:
            print(f'[{date("s")}] 正在保存用户数据')
        try:
            f = open('Data/user_data.csv', 'r+', encoding='utf-8', newline='')
            f_csv = csv.DictWriter(f, USER_DATA_HEADER)
            last_line = csv_last_line(f)
            for i in USER_DATA_HEADER[6:9]:
                if self.user_data[i] == last_line[i]:
                    self.user_data[i] = EMPTY
            if self.user_data[USER_DATA_HEADER[9]][16:] == last_line[USER_DATA_HEADER[9]][16:]:
                self.user_data[USER_DATA_HEADER[9]] = EMPTY
            f_csv.writerow(self.user_data)
        except FileNotFoundError:
            f = open('Data/user_data.csv', 'w', encoding='utf-8-sig', newline='')
            f_csv = csv.DictWriter(f, USER_DATA_HEADER)
            f_csv.writeheader()
            f_csv.writerow(self.user_data)
        return self

    def check_update(self) -> str:
        ...


class Video:
    def __init__(self, bvid: str, out_print: bool = True):
        self.bvid: str = bvid
        self.date: str = '0000-00-00'
        self.data: dict = {}
        self.out_print: bool = out_print

        self.get_data()

    def get_data(self, week: bool = False):
        if self.out_print:
            print(f'[{date("s")}] 正在抓取：{self.bvid}')
        self.data = requests.get('http://api.bilibili.com/x/web-interface/view',
                                 params={'bvid': self.bvid}).json()['data']
        self.date = date('s') if week else date('day')
        return self

    def save(self, week: bool = False):
        if self.out_print:
            print('[{0}] 正在保存{1}：[{2}] {3}.csv'
                  .format(date("s"), '(week)' if week else '', Abbreviations[self.bvid], self.bvid))
        d = {'date': self.date}
        for i in VIDEO_HEADER[1:8]:
            d[i] = self.data['stat'][i]
        for i in VIDEO_HEADER[8:]:
            d[i] = self.data[i]
        try:
            if week:
                f = open(f'Data/VideosWeek/[{Abbreviations[self.bvid]}] {self.bvid}.csv',
                         'r+', encoding='utf-8', newline='')
            else:
                f = open(f'Data/Videos/[{Abbreviations[self.bvid]}] {self.bvid}.csv',
                         'r+', encoding='utf-8', newline='')
            f_csv = csv.DictWriter(f, VIDEO_HEADER)
            last_line = csv_last_line(f)
            for i in VIDEO_HEADER[8:]:
                if d[i] == last_line[i]:
                    d[i] = EMPTY
            f_csv.writerow(d)
        except FileNotFoundError:
            if week:
                f = open(f'Data/VideosWeek/[{Abbreviations[self.bvid]}] {self.bvid}.csv',
                         'w', encoding='utf-8-sig', newline='')
            else:
                f = open(f'Data/Videos/[{Abbreviations[self.bvid]}] {self.bvid}.csv',
                         'w', encoding='utf-8-sig', newline='')
            f_csv = csv.DictWriter(f, VIDEO_HEADER)
            f_csv.writeheader()
            f_csv.writerow(d)
        f.close()
        return self


if __name__ == '__main__':
    goldeneggs = UP(13337125)
    goldeneggs.save(True)
