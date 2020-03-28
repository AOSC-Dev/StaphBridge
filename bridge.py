#! /usr/bin/env python3
import irc
#import multiprocessing as mp
## Use Threading instead... a little bit dirty though
import threading as mp
mp.Process = mp.Thread
import queue
mp.Queue = queue.Queue
#####
import tg
import sys
import time

__doc__ = sys.argv[0]+''' - TG-IRC Bot for interoperation.

Synopsis:
    '''+sys.argv[0]+''' TG-Token TG-GroupID IRC-Server IRC-Channel IRC-Nickname'''

def ircSend(ircBot,stdin,killSignal):
    while killSignal.empty():
        while not stdin.empty():
            ircBot.sendMsg(stdin.get())

def ircRecv(ircBot,stdout,killSignal):
    while killSignal.empty():
        if ircBot.handleIncomingMsg(stdout.put):
            ircBot.reconnect()

def tgSend(tgBot,groupID,stdin,killSignal):
    while killSignal.empty():
        buf = ''
        while not stdin.empty():
            buf += stdin.get()+'\n'
        if buf:
            tgBot.sendMessage(groupID,buf,{'parse_mode':'HTML'})
        time.sleep(3) # TG AntiFlood

def tgRecv(tgBot,groupID,stdout,killSignal):
    tmp = tgBot.query('getUpdates')
    lastID = None
    while killSignal.empty():
        for item in tmp:
            if item['message']['chat']['id'] == groupID:
                stdout.put(tg.getMsgText(item['message']))
            lastID = item['update_id']+1
        tmp = tgBot.query('getUpdates',{'offset':lastID,'timeout':20})
        time.sleep(1) # TG AntiFlood

def main(args):
    if len(args) != 5:
        print(__doc__)
        sys.exit()
    apikey = args[0]
    groupID = args[1]
    ircSvr = args[2]
    ircChan = args[3]
    ircName = args[4]

    tgAPI = tg.tgapi(apikey)
    # Initialize TG API complete
    ircAPI = irc.ircSocket(ircSvr,ircName)
    ircAPI.joinChannel(ircChan)
    # Initialize IRC API complete
    tgQueue = (mp.Queue(),mp.Queue())
    ircQueue = (mp.Queue(),mp.Queue())
    killSignal = mp.Queue()
    ircIn = mp.Process(target=ircRecv,args=(ircAPI,ircQueue[0],killSignal))
    ircIn.start()
    ircOut = mp.Process(target=ircSend,args=(ircAPI,ircQueue[1],killSignal))
    ircOut.start()
    tgIn = mp.Process(target=tgRecv,args=(tgAPI,groupID,tgQueue[0],killSignal))
    tgIn.start()
    tgOut = mp.Process(target=tgSend,args=(tgAPI,groupID,tgQueue[1],killSignal))
    tgOut.start()
    # Initialize IO Thread complete
    try:
        while True:
            while not ircQueue[0].empty():
                tmp = ircQueue[0].get()
                tgQueue[1].put(tmp)
            while not tgQueue[0].empty():
                tmp = tgQueue[0].get()
                ircQueue[1].put(tmp)
            time.sleep(0.2) # take a break from flood
    except KeyboardInterrupt:
        killSignal.put(None)
        ircAPI.quit()
        print('IRC disconnected')
        ircIn.join()
        ircOut.join()
        print('IRC thread finished')
        tgIn.join()
        tgOut.join()
        print('TG thread finished')
        sys.exit()

if __name__ == '__main__':
    main(sys.argv[1:])
