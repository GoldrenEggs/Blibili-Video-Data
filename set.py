from BilibiliVideoData import Abbreviations

if __name__ == '__main__':
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
        break
