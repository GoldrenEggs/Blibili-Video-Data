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
    'Cookie': 'SESSDATA=08e1eebb%2C1679035008%2C2907d*91',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/101.0.4951.54 Safari/537.36 Edg/101.0.1210.39'}

EMPTY = '〃'

VIDEO_HEADER = ('date', 'view', 'like', 'coin', 'favorite', 'share', 'danmaku', 'reply',
                'title', 'desc', 'pic')
USER_DATA_HEADER = ('date', 'following', 'follower', 'likes', 'archive', 'article',
                    'sign', 'notice', 'face', 'top_photo')
VIDEOS_DATA_HEADER = ('number', 'bvid', 'aid', 'tid', 'tname', 'title', 'pubdate', 'ctime',
                      'state', 'duration', 'dynamic', 'cid', 'width', 'height', 'is_stein_gate')


def date() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def csv_last_line(fp: IO[str]) -> dict:
    """
    读取 CSV 文件，并返回没有空值的一行

    :param fp: 文件IO
    :type fp: IO[str]
    """
    f_csv = csv.DictReader(fp)
    d = {k: None for k in f_csv.fieldnames}
    for line in reversed(list(f_csv)):
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
        """
        获取对应账号所有视频的BV号列表
        """
        if self.out_print:
            print(f'[{date()}] 正在抓取视频列表')
        videos_bvid = []
        space = requests.get('http://api.bilibili.com/x/space/arc/search',
                             params={'mid': self.mid}, headers=HEADERS).json()
        page_number = ceil(space['data']['page']['count'] / space['data']['page']['ps'])
        for page in range(1, page_number + 1):
            r = requests.get('http://api.bilibili.com/x/space/arc/search',
                             params={'mid': self.mid, 'pn': page}, headers=HEADERS)
            video_list = r.json()['data']['list']['vlist']
            videos_bvid.extend(video_list[i]['bvid'] for i in range(len(video_list)))
        self.videos_bvid = videos_bvid
        print(f'[{date()}] 已取得视频列表：', *videos_bvid)
        return self

    def get_videos(self):
        """
        根据存储的bvid列表，创建对应的视频实例。
        """
        videos = [Video(bvid) for bvid in self.videos_bvid]
        self.videos = videos
        return self

    def get_user_data(self):
        """
        获取并保存用户的信息。
        """
        if self.out_print:
            print(f'[{date()}] 正在抓取用户数据', end='')
        user_data = {'date': date()[:10], 'following': None, 'follower': None, 'likes': None, 'archive': None,
                     'article': None, 'sign': None, 'notice': None, 'face': None, 'top_photo': None}

        r = requests.get('http://api.bilibili.com/x/relation/stat', params={'vmid': self.mid}).json()['data']
        user_data['following'] = r['following']  # 关注数
        user_data['follower'] = r['follower']  # 粉丝数

        r = requests.get('http://api.bilibili.com/x/space/upstat', params={'mid': self.mid}, headers=HEADERS).json()[
            'data']
        user_data['likes'] = r['likes']  # 点赞数
        user_data['archive'] = r['archive']['view']  # 播放数
        user_data['article'] = r['article']['view']  # 阅读数

        r = requests.get('http://api.bilibili.com/x/space/acc/info', params={'mid': self.mid}, headers=HEADERS).json()[
            'data']
        user_data['sign'] = r['sign']  # 签名
        user_data['face'] = r['face']  # 头像
        user_data['top_photo'] = r['top_photo']  # 头图

        r = requests.get('http://api.bilibili.com/x/space/notice', params={'mid': self.mid}).json()['data']
        user_data['notice'] = r  # 公告

        self.user_data = user_data
        if self.out_print:
            print('  完成')
        return self

    def save_videos_raw_data(self):
        if self.out_print:
            print(f'[{date()}] 正在保存视频原始数据')
        raw_data = [video.data for video in self.videos]
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
        with open('Data/VideosData.csv', 'r', encoding='utf-8-sig') as f:
            videos_bvid.extend(row['bvid'] for row in csv.DictReader(f))
        new_videos_bvid = [check_video_bvid for check_video_bvid in check_videos_bvid if
                           check_video_bvid not in videos_bvid]
        if auto_update_videos_data:
            for bvid in reversed(new_videos_bvid):
                self.update_videos_data(bvid)
                Abbreviations.add(bvid)
        return tuple(reversed(new_videos_bvid))

    def update_videos_data(self, bvid: str):
        video_data = requests.get('http://api.bilibili.com/x/web-interface/view', params={'bvid': bvid}).json()['data']
        with open('Data/VideosData.csv', 'a', encoding='utf-8-sig', newline='') as f_videos_data:
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

    def check_new_videos(self, day: int = 14) -> tuple:
        """
        返回在day天数内更新的视频实例

        @param day: 检测跨度
        @return: Video实例元组
        """
        new_videos_bvid = self.check_new_videos_bvid(day)
        new_videos: List[Video] = [video for video in self.videos if video.bvid in new_videos_bvid]
        if self.out_print:
            if new_videos_bvid:
                print(f'\n[{date()}] 已找到视频：', *[Abbreviations[bvid] for bvid in new_videos_bvid])
            else:
                print('  未找到')
        return tuple(reversed(new_videos))

    def check_new_videos_bvid(self, day: int):  # 返回在day天内更新的视频BV号
        if self.out_print:
            print(f'[{date()}] 正在查找{day}天内更新的视频', end='')
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
        req = requests.get('http://api.bilibili.com/x/web-interface/view', params={'bvid': self.bvid}).json()
        if req['code'] == 0:
            self.data = req['data']
            self.date = date()
            print('  成功')
        else:
            print(f'  失败 {str(req)}')
        return self

    def save(self, is_hour: bool = False):
        if self.out_print:
            print('[{0}] 正在保存：[{1}] {2}.csv'.format(date(), Abbreviations[self.bvid], self.bvid))
        d = {'date': self.date if is_hour else self.date[:10]}
        for i in VIDEO_HEADER[1:8]:
            d[i] = self.data['stat'][i]
        for i in VIDEO_HEADER[8:]:
            d[i] = self.data[i]
        path = f'{VIDEOS_HOUR_PATH}/[{Abbreviations[self.bvid]}] {self.bvid}.csv' if is_hour else \
            f'{VIDEOS_PATH}[{Abbreviations[self.bvid]}] {self.bvid}.csv'
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
        for k, v in cls.abbreviations.items():
            if v == item:
                return k

    @classmethod
    def rename(cls, bvid: str = '', name: str = ''):
        confirm = 'Y'
        if not bvid:
            bvid = input('\n请输入BV号：')
        if bvid not in cls.abbreviations.keys():
            print('该BV号不存在。')
            return
        if not name:
            name = input(f'当前简称：【{cls[bvid]}】\n请输新入简称：')  # 要求用户确认视频名称的更改。
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
        for row in csv.DictReader(open('Data/VideosData.csv', 'r', encoding='utf-8-sig')):
            if row['bvid'] == bvid:
                name = row['title'][:6]
        cls.abbreviations[bvid] = name
        d = {bvid: name}
        d |= cls.abbreviations
        cls.abbreviations = d
        with open('Data/Abbreviations.json', 'w', encoding='utf-8') as f:
            json.dump(cls.abbreviations, f, ensure_ascii=False, indent=4)

    @classmethod
    def test(cls):
        print(type(cls.abbreviations))


if __name__ == '__main__':
    goldeneggs = UP(13337125)
    goldeneggs.save()
