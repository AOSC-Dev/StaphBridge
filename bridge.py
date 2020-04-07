#! /usr/bin/env python3
import irc
#import multiprocessing as mp
import threading as mp
mp.Process = mp.Thread
import queue
mp.Queue = queue.Queue
#####
import tg
import sys
import time

def ircSend(ircBot,stdin,killSignal):
    while killSignal.empty():
        while not stdin.empty():
            ircBot.sendMsg(stdin.get())
        time.sleep(0.2)

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
            if 'message' in item:
                if item['message']['chat']['id'] == groupID:
                    stdout.put(tg.getMsgText(item['message']))
            else:
                print(repr(item))
            lastID = item['update_id']+1
        tmp = tgBot.query('getUpdates',{'offset':lastID,'timeout':20})
        time.sleep(1) # TG AntiFlood

def main():
    apikey = '123456789:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' # Your TG API Key
    groupID = -100123456789 # Your TG Group
    ircChan = '#ircchannel'
    ircName = 'BridgeBot'
    ircSvr = 'irc.freenode.net'

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
        ircIn.join()
        ircOut.join()
        tgIn.join()
        tgOut.join()
        sys.exit()

if __name__ == '__main__':
    main()
