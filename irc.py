#! /usr/bin/env python3
import socket
import ssl
import sys
import time
import urllib.parse as up
import urllib.request as ur

def parseMessage(ircmsg):
    ## DEBUG
    #print(repr(ircmsg))
    result = {}
    if ircmsg.find("PRIVMSG") != -1:
        result['name'] = ircmsg.split('!',1)[0][1:]
        result['chan'] = ircmsg.split('PRIVMSG ',1)[1].split(' ',1)[0]
        result['text'] = ircmsg.split('PRIVMSG',1)[1].split(':',1)[1]
        if result['text'][:7] == '\x01ACTION':
            result['config']={'irc_action':True}
            result['text'] = result['text'][7:-1]
    elif ircmsg.find("JOIN") != -1:
        result['name'] = ircmsg.split('!',1)[0][1:]
        result['chan'] = ircmsg.split('JOIN ',1)[1].split(' ',1)[0].strip()
        result['text'] = 'has joined this channel.'
        result['config'] = {'irc_join':True}
    elif ircmsg.find("PART") != -1 or ircmsg.find("QUIT") != -1:
        result['name'] = ircmsg.split('!',1)[0][1:]
        result['chan'] = ircmsg.split('PART ' if ircmsg.find("PART") != -1 else 'QUIT ',1)[1].split(' ',1)[0].strip()
        result['text'] = 'has left this channel.'
        result['config'] = {'irc_quit':True}
    elif ircmsg != None:
        print(repr(ircmsg))
        result = {'name':'unknown','chan':'unknown','text':repr(ircmsg),'config':{'irc_error':True}}
    else:
        result = None
        return result
    return (('irc',result.pop('chan')),result)

class ircSocket:
    def __init__(self,server,botnick,port=6697):
        self.server = server
        self.port = port
        self.nick = botnick
        self.channel = []
        self.sock = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2).wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
        self.sock.connect((server, port))
        self.sock.send(bytes("USER "+ botnick +" "+ botnick +" "+ botnick + " " + botnick + "\n", "UTF-8")) #We are basically filling out a form with this line and saying to set all the fields to the bot nickname.
        self.sock.send(bytes("NICK "+ botnick +"\n", "UTF-8")) # assign the nick to the bot
        self.quitNow = False

    def joinChannel(self,channel):
        self.sock.send(bytes("JOIN "+ channel +"\n", "UTF-8")) 
        ircmsg = ""
        while ircmsg.find("End of /NAMES list.") == -1:  
            ircmsg = self.sock.recv(2048).decode("UTF-8")
            ircmsg = ircmsg.strip('\n\r')
            #print(ircmsg)
        self.channel.append(channel)
        #DEBUG:
        print("["+str(int(time.time()))+"] Bot "+self.nick+" successfully joined IRC channel "+channel)
        #print(ircmsg)

    def identifyNick(self,password):
        ircmsg= ''
        while ircmsg[:9] != ':NickServ':
            ircmsg = self.sock.recv(2048).decode("UTF-8").strip('\n\r')
        print(ircmsg)
        ircmsg = ''
        self.sock.send(bytes('PRIVMSG NickServ :identify '+password+'\r\n','UTF-8'))
        while ircmsg[:9] != ':NickServ':
            ircmsg = self.sock.recv(2048).decode("UTF-8").strip('\n\r')
        print(ircmsg)

    def reconnect(self):
        print("RECONNECT requested")
        if self.quitNow:
            time.sleep(1)
            return 1
        self.sock = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2).wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
        self.sock.connect((self.server, self.port))
        self.sock.send(bytes("USER "+ self.nick +" "+ self.nick +" "+ self.nick + " " + self.nick + "\r\n", "UTF-8")) #We are basically filling out a form with this line and saying to set all the fields to the bot nickname.
        self.sock.send(bytes("NICK "+ self.nick +"\r\n", "UTF-8")) # assign the nick to the bot
        channel = self.channel
        self.channel = []
        for c in channel:
            self.joinChannel(c)

    def handleIncomingMsg(self,msgHandler=None):
        '''Handles one incoming message.
        Return 0 on Success
        Return 1 on Error'''
        ircmsg = self.sock.recv(2048).decode("UTF-8")
        ircmsg = ircmsg.strip('\n\r')
        if ircmsg[:4] == "PING":
            self.sock.send(bytes("PONG :"+self.nick+"\r\n", "UTF-8"))
            #print("I have just got a ping... "+ircmsg)
            return 0
        elif ircmsg == '':
            print("I might have been disconnected... Please restart me.")
            return 1
        elif ircmsg.find("PRIVMSG") != -1: # ONLY handle PRIVMSG
            return msgHandler(parseMessage(ircmsg))
        else:
            return 0

    def sendMessage(self,chan,msg):
        if chan not in self.channel:
            raise ValueError("Message goes to channel"+chan+" that I have not joined. I am in "+repr(self.channel))
        for item in msg.split('\n'):
            if item:
                while len(item) > 128:
                    self.sock.send(bytes("PRIVMSG "+chan+" :"+item[:128]+"\r\n","UTF-8"))
                    time.sleep(0.1)
                    item = item[128:]
                if item.strip():
                    self.sock.send(bytes("PRIVMSG "+chan+" :"+item+"\r\n","UTF-8"))
                    time.sleep(0.1)

    def quit(self):
        self.sock.send(bytes("QUIT","UTF-8"))
        self.quitNow = True

def main():
    server = "chat.freenode.net" # Server
    channel = "##offtopic" # Channel
    botnick = "BridgeBot" # Your bots nick

    ircSrv = ircSocket(server,botnick)
    ircSrv.joinChannel(channel)

    print("Successfully joined the channel "+channel)

    status = True
    while status:
        try:
            status = 0 == ircSrv.handleIncomingMsg()
        except KeyboardInterrupt:
            print("Quitting...")
            ircSrv.quit()
            status = False

if __name__ == '__main__':
    main()
