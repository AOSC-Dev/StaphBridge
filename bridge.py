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

def transMap(mapping,progList):
    result = {}
    for item in progList:
        result[item] = []
    for item in mapping:
        for prog in progList:
            result[prog].append(item[prog] if prog in item else None)
    return result

def escapeTG(msg):
    return msg.replace('&','&amp;').replace('>','&gt;').replace('<','&lt;')

def msgToTG(msg,src):
    prefix = {'irc':'&lt;I&gt; '}
    if 'config' in msg and 'irc_action' in msg['config']:
        return prefix[src] + '* <b>'+escapeTG(msg['name'])+'</b> '+escapeTG(msg['text'])
    else:
        return prefix[src] + '[<b>'+escapeTG(msg['name'])+'</b>] '+escapeTG(msg['text'])

def msgToIRC(msg,src):
    prefix = {'tg':'<T> '}
    return prefix[src] + '['+msg['name']+'] '+msg['text']

def msgToLog(msg,src):
    prefix = {'tg':'<TG>','irc':'<IRC>'}
    return str(int(time.time()) +'\t'+ prefix[src] + '\t[' + msg['name'] + '] '+msg['text']+'\n'

def logSend(mapping,stdin,killSignal):
    while killSignal.empty():
        while not stdin.empty():
            tmp = stdin.get()
            if tmp[0][0] != 'log' and tmp[0][1] in mapping[tmp[0][0]] and mapping['log'][mapping[tmp[0][0]].index(tmp[0][1])] is not None:
                mapping['log'][mapping[tmp[0][0]].index(tmp[0][1])].write(msgToLog(tmp[0][0],msgToLog(tmp[1])))
        time.sleep(1)

def logRecv(stdout,killSignal):
    while killSignal.empty():
        time.sleep(10)

def ircSend(ircBot,mapping,stdin,killSignal):
    while killSignal.empty():
        while not stdin.empty():
            tmp = stdin.get()
            if tmp[0][0] != 'irc' and tmp[0][1] in mapping[tmp[0][0]] and mapping['irc'][mapping[tmp[0][0]].index(tmp[0][1])] is not None:
                chan = mapping['irc'][mapping[tmp[0][0]].index(tmp[0][1])]
                ircBot.sendMessage(chan,msgToIRC(tmp[1],tmp[0][0]))
        time.sleep(0.2)

def ircRecv(ircBot,stdout,killSignal):
    while killSignal.empty():
        if ircBot.handleIncomingMsg(stdout.put):
            ircBot.reconnect()

def tgSend(tgBot,mapping,stdin,killSignal):
    while killSignal.empty():
        buf = {}
        while not stdin.empty():
            tmp = stdin.get()
            if tmp[0][0] != 'tg' and tmp[0][1] in mapping[tmp[0][0]] and mapping['tg'][mapping[tmp[0][0]].index(tmp[0][1])] is not None:
                if mapping['tg'][mapping[tmp[0][0]].index(tmp[0][1])] not in buf:
                    buf[mapping['tg'][mapping[tmp[0][0]].index(tmp[0][1])]] = ''
                buf[mapping['tg'][mapping[tmp[0][0]].index(tmp[0][1])]] += msgToTG(tmp[1],tmp[0][0])+'\n'
        for item in buf:
            tgBot.sendMessage(item,buf[item],{'parse_mode':'HTML'})
        time.sleep(3) # TG AntiFlood

def tgRecv(tgBot,stdout,killSignal):
    tmp = tgBot.query('getUpdates')
    lastID = None
    while killSignal.empty():
        for item in tmp:
            if 'message' in item:
                stdout.put(tg.getMsg(item['message']))
            else:
                print(repr(item))
            lastID = item['update_id']+1
        tmp = tgBot.query('getUpdates',{'offset':lastID,'timeout':20})
        time.sleep(1) # TG AntiFlood

def main():
    ### Customize this before running
    apikey = '123456789:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' # Your TG API Key
    ircName = 'BridgeBot'
    ircSvr = 'irc.freenode.net'

    programs = ['tg','irc','log']
    mapping = [{'tg':-1001000000000,'irc':'##offtopic','log':open('offtopic.log')},{'tg':-1001234567890,'irc':'##bottest'}]
    ### Customize ends here

    mapT = transMap(mapping,programs)
    tgAPI = tg.tgapi(apikey)
    # Initialize TG API complete
    ircAPI = irc.ircSocket(ircSvr,ircName)
    for ircChan in mapT['irc']:
        ircAPI.joinChannel(ircChan)
    # Initialize IRC API complete
    inQueue = []
    outQueue = []
    for item in programs:
        inQueue.append(mp.Queue())
        outQueue.append(mp.Queue())
    killSignal = mp.Queue()
    ircIn = mp.Process(target=ircRecv,args=(ircAPI,inQueue[programs.index('irc')],killSignal))
    ircOut = mp.Process(target=ircSend,args=(ircAPI,mapT,outQueue[programs.index('irc')],killSignal))
    tgIn = mp.Process(target=tgRecv,args=(tgAPI,inQueue[programs.index('tg')],killSignal))
    tgOut = mp.Process(target=tgSend,args=(tgAPI,mapT,outQueue[programs.index('tg')],killSignal))
    logIn = mp.Process(target=logRecv,args=(inQueue[programs.index('log')],killSignal))
    logOut = mp.Process(target=logSend,args=(mapT,outQueue[programs.index('log')],killSignal))
    # Initialize IO Thread complete
    try:
        ircIn.start()
        ircOut.start()
        tgIn.start()
        tgOut.start()
        logIn.start()
        logOut.start()
        while True:
            for progIn in inQueue:
                while not progIn.empty():
                    tmp = progIn.get()
                    for progOut in outQueue:
                        progOut.put(tmp)
            time.sleep(0.4) # take a break from flood
    except KeyboardInterrupt:
        killSignal.put(None)
        ircIn.join()
        ircOut.join()
        tgIn.join()
        tgOut.join()
        logIn.join()
        logOut.join()
        ircAPI.quit()
        sys.exit()

if __name__ == '__main__':
    main()
