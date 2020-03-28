#! /usr/bin/env python3
import socket
import ssl
import sys
import time
import urllib.parse as up
import urllib.request as ur

def escapeTG(msg):
    return msg.replace('&','&amp;').replace('>','&gt;').replace('<','&lt;')

def parseMessage(ircmsg):
    ## DEBUG
    #print(repr(ircmsg))
    if ircmsg.find("PRIVMSG") != -1:
        name = ircmsg.split('!',1)[0][1:]
        message = escapeTG(ircmsg.split('PRIVMSG',1)[1].split(':',1)[1])
        if message[:7] == '\x01ACTION':
            return '* <b>'+name+'</b>'+message[7:-1]
        else:
            return '[<b>'+name+"</b>] "+message
    elif ircmsg.find("JOIN") != -1:
        name = ircmsg.split('!',1)[0][1:]
        return '# <b>'+name+"</b> has joined this channel."
    elif ircmsg.find("PART") != -1 or ircmsg.find("QUIT") != -1:
        name = ircmsg.split('!',1)[0][1:]
        return '# <b>'+name+"</b> has left this channel."
    elif ircmsg != None:
        print(repr(ircmsg))
        return repr(ircmsg)

def sendTG(msg):

    ## TG Configuration
    ## ONLY used if you are running it standalone
    ## as an IRC -> TG one-way bridge
    ## Not responsible for TG AntiFlood
    botToken = 'GET_YOUR_OWN_TOKEN'
    groupID = 'YOUR GROUP ID (in int)'
    #### UPDATE THIS BEFORE USE ####
    reqSecret = {'chat_id':groupID,'text':msg,'parse_mode':'HTML'}
    reqData = up.urlencode(reqSecret).encode("UTF-8")
    req = ur.Request("https://api.telegram.org/bot"+botToken+'/sendMessage',data=reqData,method="POST")
    resp = ur.urlopen(req)
    print("The TG msg was sent with code "+str(resp.status))
    return 0 if resp.status == 200 else 1

class ircSocket:
    def __init__(self,server,botnick,port=6697):
        self.server = server
        self.port = port
        self.nick = botnick
        self.channel = None
        self.sock = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2).wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
        self.sock.connect((server, port))
        self.sock.send(bytes("USER "+ botnick +" "+ botnick +" "+ botnick + " " + botnick + "\n", "UTF-8")) #We are basically filling out a form with this line and saying to set all the fields to the bot nickname.
        self.sock.send(bytes("NICK "+ botnick +"\n", "UTF-8")) # assign the nick to the bot

    def joinChannel(self,channel):
        if self.channel is not None:
            self.sock.send(bytes("PART "+self.channel+"\n","UTF-8"))
        self.sock.send(bytes("JOIN "+ channel +"\n", "UTF-8")) 
        ircmsg = ""
        while ircmsg.find("End of /NAMES list.") == -1:  
            ircmsg = self.sock.recv(2048).decode("UTF-8")
            ircmsg = ircmsg.strip('\n\r')
        self.channel = channel
        #DEBUG:
        print("["+str(int(time.time()))+"] Bot "+self.nick+" successfully joined IRC channel "+channel)
        #print(ircmsg)

    def reconnect(self):
        if self.quit:
            time.sleep(1)
            return 1
        self.sock = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2).wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
        self.sock.connect((self.server, self.port))
        self.sock.send(bytes("USER "+ self.nick +" "+ self.nick +" "+ self.nick + " " + self.nick + "\n", "UTF-8")) #We are basically filling out a form with this line and saying to set all the fields to the bot nickname.
        self.sock.send(bytes("NICK "+ self.nick +"\n", "UTF-8")) # assign the nick to the bot
        channel = self.channel
        self.channel = None
        self.joinChannel(channel)

    def handleIncomingMsg(self,msgHandler=sendTG):
        '''Handles one incoming message.
        Return 0 on Success
        Return 1 on Error'''
        ircmsg = self.sock.recv(2048).decode("UTF-8")
        ircmsg = ircmsg.strip('\n\r')
        if ircmsg[:4] == "PING":
            self.sock.send(bytes("PONG :"+self.nick, "UTF-8"))
            print("I have just got a ping... "+ircmsg)
            return 0
        elif ircmsg == '':
            print("I might have been disconnected... Please restart me.")
            return 1
        elif ircmsg.find("PRIVMSG") != -1: # ONLY handle PRIVMSG
            return msgHandler(parseMessage(ircmsg))
        else:
            return 0

    def sendMsg(self,msg):
        self.sock.send(bytes("PRIVMSG "+self.channel+" :"+msg+"\n","UTF-8"))

    def quit(self):
        self.sock.send(bytes("QUIT","UTF-8"))
        self.quit = True

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
