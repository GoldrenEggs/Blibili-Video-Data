from threading import Thread

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
    Thread(target=scheduler.start, args=(), daemon=True).start()
    while True:
        command = input('Command: ').split(' ')
        if command[0] == 'q' or command[0] == 'quit':
            break
        elif command[0] == 'rename':
            Abbreviations.rename()
        elif command[0] == 'all_name':
            print(Abbreviations.abbreviations)
        else:
            continue
