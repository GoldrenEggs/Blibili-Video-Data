from apscheduler.schedulers.blocking import BlockingScheduler

from BilibiliVideoData import UP, Abbreviations


def day():
    goldeneggs.get().save()


def hour():
    update_videos = goldeneggs.check_update()
    if update_videos:
        print('TNND，你还知道更新啊？', *update_videos)

    goldeneggs.get_and_save_hour()


if __name__ == '__main__':
    uid = 13337125
    goldeneggs = UP(uid, auto_get=True)
    scheduler = BlockingScheduler(timezone='Asia/Shanghai')
    scheduler.add_job(day, 'cron', hour=23, minute=50)
    scheduler.add_job(hour, 'cron', hour='0-23', minute=5)
    scheduler.start()
    while True:
        command = input('command:').split(' ')
        if command[0] == 'rename':
            Abbreviations.rename()
