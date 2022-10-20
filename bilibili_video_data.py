import csv
import json
import os
import time
from math import ceil
from threading import Thread
from typing import IO, List, Tuple
import yaml

import py7zr
import requests

with open('config.yaml', 'r', encoding='utf-8') as config:
    config = yaml.safe_load(config)
    base_path = config['Path']
    HEADERS = config['Headers']
    EMPTY = config['EmptyChar']


    class Path:
        VIDEOS = base_path['Videos']
        VIDEOS_RAW = base_path['VideosRaw']
        VIDEOS_HOUR = base_path['VideosHour']
        VIDEOS_HOUR_RAW = base_path['VideosHourRaw']
        ABBREVIATIONS = base_path['Abbreviations']
        USER_DATA = base_path['UserData']
        VIDEOS_DATA = base_path['VideosData']


class CsvHeader:
    VIDEO = ('date', 'view', 'like', 'coin', 'favorite', 'share', 'danmaku', 'reply',
             'title', 'desc', 'pic')
    USER_DATA = ('date', 'following', 'follower', 'likes', 'archive', 'article',
                 'sign', 'notice', 'face', 'top_photo')
    VIDEOS_DATA = ('number', 'bvid', 'aid', 'tid', 'tname', 'title', 'pubdate', 'ctime',
                   'state', 'duration', 'dynamic', 'cid', 'width', 'height', 'is_stein_gate')


@property
def date() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def csv_last_line(fp: IO[str]) -> dict:
    """
    倒叙读取 CSV 文件，返回以不为空字符组成的字典

    :param fp: 文件IO
    :type fp: IO[str]
    """
    f_csv = csv.DictReader(fp)
    result = {k: None for k in f_csv.fieldnames}
    for line in reversed(list(f_csv)):
        for key in line:
            if result[key] in (None, EMPTY):
                result[key] = line[key]
        if EMPTY not in result.values():
            break
    return result


class Video:
    out_print = True

    @classmethod
    def print(cls, *args, **kwargs):
        if cls.out_print:
            print(*args, **kwargs)

    @classmethod
    def get(cls, bvid: str) -> dict:
        cls.print(f'[{date}] 正在抓取：{bvid}', end='')
        req = requests.get('http://api.bilibili.com/x/web-interface/view',
                           params={'bvid': bvid}, headers=HEADERS).json()
        if req['code'] == 0:
            data = req['data']
            cls.print(f"  成功  【{data['title']}】")
            return data
        else:
            cls.print(f"  失败 {str(req)}  {req}")
            return {}

    @classmethod
    def save(cls, data: dict, is_hour: bool = False):
        now = date
        bvid = data['bvid']
        cls.print('[{0}] 正在保存：[{1}] {2}.csv'.format(now, Abbreviations[bvid], bvid))
        d = {'date': now if is_hour else now[:10]}
        for i in CsvHeader.VIDEO[1:8]:
            d[i] = data['stat'][i]
        for i in CsvHeader.VIDEO[8:]:
            d[i] = data[i]
        path = f'{Path.VIDEOS_HOUR}/[{Abbreviations[bvid]}] {bvid}.csv' if is_hour \
            else f'{Path.VIDEOS}[{Abbreviations[bvid]}] {bvid}.csv '
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


class Abbreviations:
    with open('Data/Abbreviations.json', 'r', encoding='utf-8') as f:
        abbreviations: dict = json.load(f)

    def __class_getitem__(cls, item):
        if item[:2] == 'BV':
            return cls.abbreviations.get(item)
        for k, v in cls.abbreviations.items():
            if v == item:
                return k

    @classmethod
    def save(cls):
        with open(Path.ABBREVIATIONS, 'w', encoding='utf-8') as file:
            json.dump(cls.abbreviations, file, ensure_ascii=False, indent=4)

    @classmethod
    def rename(cls, bvid: str = '', name: str = ''):
        if not bvid:
            bvid = input('\n请输入BV号/视频简称：')
            if bvid[:2] != 'BV':
                if bvid := cls[bvid]:
                    bvid = bvid
                else:
                    print('该简称不存在。')
                    return
        if bvid not in cls.abbreviations.keys():
            print('该BV号不存在。')
            return
        confirm = 'yes'
        if not name:
            name = input(f'当前简称：【{cls[bvid]}】\n请输新入简称：')
            confirm = input(f'确认将{bvid}：【{cls[bvid]}】 修改为 【{name}】 吗？(Y/N)')
        if confirm in ('Y', 'y', 'yes'):
            src = f"{Path.VIDEOS}[{cls[bvid]}] {bvid}.csv"
            dst = f"{Path.VIDEOS}[{name}] {bvid}.csv"
            src_hour = f"{Path.VIDEOS_HOUR}[{cls[bvid]}] {bvid}.csv"
            dst_hour = f"{Path.VIDEOS_HOUR}[{name}] {bvid}.csv"
            src_hour_raw = f"{Path.VIDEOS_HOUR_RAW}[{cls[bvid]}] {bvid}.7z"
            dst_hour_raw = f"{Path.VIDEOS_HOUR_RAW}[{name}] {bvid}.7z"
            os.rename(src, dst)
            os.rename(src_hour, dst_hour)
            os.rename(src_hour_raw, dst_hour_raw)
            cls.abbreviations[bvid] = name
            cls.save()

    @classmethod
    def add(cls, bvid: str, name: str):
        d = {bvid: name[:6]}
        d |= cls.abbreviations
        cls.abbreviations = d
        cls.save()


class Log:
    out_print = True
    ...


def main():
    bvid = 'BV1dV4y1N7kZ'
    data = Video.get(bvid)
    print(data)


if __name__ == '__main__':
    main()
