import socket
from getpass import getpass
import threading
import queue
import struct

packet_len_pack_pattern = 'Q'
sizeBytes = 8

def sendPacket(sock, bstr):
    sock.send(struct.pack(packet_len_pack_pattern, len(bstr)))
    sock.send(bstr)
    recvBytes(sock, 1)

def recvPacket(sock):
    packet_len_bstr = recvBytes(sock, sizeBytes)
    packet_len = struct.unpack(packet_len_pack_pattern, packet_len_bstr)[0]
    bstr = recvBytes(sock, packet_len)
    sock.send(b'0')
    return bstr

def recvBytes(sock, count):
    bstr = b''
    while count > 0:
        b = sock.recv(count)
        count -= len(b)
        bstr += b
    return bstr

class InteractionMode:
    def __init__(self):
        self.user_id = '-1'
        self.opening_rooms_id = []
        self.recv_message_queue = queue.Queue()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #TCP
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #can repeated use the port
        self.socket.settimeout(1)
        self.connected=False
        while(not self.connected):
            try:
                self.socket.connect(('127.0.0.1', 12345))
                self.connected=True
            except Exception as e:
                print('In __init__', e)
        while(1):
            funcs = '>you can enter'
            funcs += "login, "
            funcs += "logout, "
            funcs += "listuser, "
            funcs += 'listonlineuser, '
            funcs += "listchatRoom, "
            funcs += "joinchatRoom, "
            funcs += "leavechatRoom, "
            funcs += "showopeningchatrooms, "
            funcs += "talk, "
            funcs += "talkinroom, "
            funcs += "broadcast"
            funcs += "(make sure not to spell wrong)"
            print(funcs)
            if self.user_id == '-1':
                command = input('>')
            else:
                command = input('(Logged in, uid:'+str(self.user_id)+')>')
            self.CommandJudge(command)

    def CommandJudge(self, user_command):
        if user_command == 'createaccount':
            self.CreateAccount()
        elif user_command == 'login':
            self.LogIn()
        elif user_command == 'logout':
            self.LogOut()
        elif user_command == 'listuser':
            self.ListUser()
        elif user_command == 'listonlineuser':
            self.ListOnlineUser()
        elif user_command == 'listchatroom':
            self.ListChatRoom()
        elif user_command == 'joinchatroom':
            if self.user_id == '-1':
                print('>You have not logged in!Please log in to join room.')
                return
            print('>Input room id to join')
            self.ListChatRoom()
            room_id = input('(Logged in, uid:'+str(self.user_id)+')>')
            if room_id in self.opening_rooms_id:
                print('>You are already in this room!')
                return
            self.JoinChatRoom(room_id)         
        elif user_command == 'leavechatroom':
            if self.user_id == '-1':
                print('>You have not logged in!No need to leave room')
                return
            print('>Input room id to leave(Now you are in:)')
            self.ShowOpeningChatRooms()
            room_id = input('(Logged in, uid:'+str(self.user_id)+')>')
            if room_id not in self.opening_rooms_id:
                print('>You are not in this room!')
                return
            self.LeaveChatRoom(room_id) 
        elif user_command == "showopeningchatrooms":
            self.ShowOpeningChatRooms()        
        elif user_command == "talk":
            if self.user_id == '-1':
                print('>You have to log in to talk!')
                return
            self.ListUser()
            print('>Talk to whom?(Please input an uid)')
            talk_to_whom = input('(Logged in, uid:'+str(self.user_id)+')>')
            try:
                int(talk_to_whom)
            except:
                print('>You are not entering an uid!')
                return
            self.FindCorrectRoom(talk_to_whom)
        elif user_command == 'broadcast':
            content = input('>what to broadcast?(input message)')
            self.Broadcast(content)
        elif user_command == "talkinroom":
            print('>You are now in these rooms:')
            self.ShowOpeningChatRooms()
            room_id = input('>which room to talk?(input RId)')
            if not room_id in self.opening_rooms_id:
                print('Sorry, You are not in this room.')
                return
            self.Talking(room_id)
        else:
            print('>Comman not found: you might spell wrong')
            return
    
    def CreateAccount(self):
        pass
        
    def LogIn(self):
        print('>Input your name below')
        name = input('>')
        print('>Input your pwd below')
        pwd = getpass()
        self.user_id = self.GetUserId(name, pwd)
        if self.user_id == '-1':
            print('>No pre-build name/pwd pair')
        else:
            print('>Logged in!')
        try:
            count_msg = recvPacket(self.socket).decode('utf8')
            if not int(count_msg)==0:
                pkg = recvPacket(self.socket).decode('utf8')
                for each in pkg.split(';'):
                    t =  each.split(':')
                    print('>from:%s\t=>%s'%(t[1], t[0]))
        except:
            pass
        
    def GetUserId(self, name, pwd):
        '''connect to server to get id of input Name/password'''
        '''return -1 when log in failed, or return user id'''
        id = '-1'

        try:
            pkg = 'login;'+name+';'+pwd+';'
            sendPacket(self.socket, (pkg).encode('utf8'))
        except Exception as e:
            print('In GetUserId', e)
        try:
            id = recvPacket(self.socket).decode('utf8')
        except Exception as e:
            print('In GetUserId2', e)
        return id
    
    def LogOut(self):
        try:
            sendPacket(self.socket, ('logout;'+self.user_id+';').encode('utf8'))
            self.user_id = '-1'
            self.opening_rooms_id = []
            print('>Logged out!')
        except Exception as e:
            print('In LogOut', e)
        
    def ListUser(self):
        try:
            sendPacket(self.socket, ('listuser;'+self.user_id+';').encode('utf8'))
        except:
            print('In ListUser: send pkg fail')
        try:
            user_list = recvPacket(self.socket).decode('utf8').split(';')
            print(user_list)
            print('>user_list:')
            if '' in user_list:
                user_list.remove('')
            for each in user_list:
                '''user_data: id, name'''
                user_data = each.split(':')
                if '' in user_data:
                    user_data.remove('')
                print('>UId:%s;Name:%s'%(user_data[0], user_data[1]))
        except Exception as e:
            print('In ListUser', e)
            
    def ListOnlineUser(self):
        try:
            sendPacket(self.socket, ('listonlineuser;'+self.user_id+';').encode('utf8'))
        except Exception as e:
            print('In ListOnlineUser:', e)
        try:
            list = recvPacket(self.socket).decode('utf8').split(';')
            print('>Online user:')
            if '' in list:
                list.remove('')
            for each in list:
                data = each.split(':')
                if '' in data:
                    data.remove('')
                print('>UId:%s;Name:%s'%(data[0], data[1]))
        except Exception as e:
            print('In ListOnlineUser:', e)
            

    def ListChatRoom(self):
        try:
            sendPacket(self.socket, ('listchatroom;'+self.user_id+';').encode('utf8'))
        except:
            print('In ListChatRoom: send pkg fail')
        try:
            room_list = recvPacket(self.socket).decode('utf8').split(';')
            print('room_list:')
            if '' in room_list:
                room_list.remove('')
            for each in room_list:
                '''room_data:id, member1[, member2...]'''
                room_data = each.split(':')
                if '' in room_data:
                    room_data.remove('')
                room_data_output = 'Rid:' + room_data[0] + ';Members:'
                for x in range(len(room_data)-1):
                    room_data_output +=  room_data[x+1]
                    room_data_output += ' '
                print(room_data_output)
        except Exception as e:
            print('In ListChatRoom', e)
    
    def JoinChatRoom(self, room_id):
        try:
            sendPacket(self.socket, ('joinchatroom;'+room_id+';'+self.user_id+';').encode('utf8'))
        except Exception as e:
            print('>In JoinChatRoom:', e)
        try:
            reply = recvPacket(self.socket).decode('utf8')
            if reply == '':
                print('>Target chatroom is not exist')
            else:
                self.opening_rooms_id.append(reply)
                print('>Join room!')
                print('>Now you are opening room:')
                self.ShowOpeningChatRooms()
        except Exception as e:
                print('In JoinChatRoom:', e)
                
    def LeaveChatRoom(self, room_id):
        try:
            sendPacket(self.socket, ('leavechatroom;'+room_id+';'+self.user_id+';').encode('utf8'))
        except Exception as e:
            print('>In JoinChatRoom:', e)
        try:
            reply = recvPacket(self.socket).decode('utf8')
            if reply == '':
                print('>You are not in target room')
            else:
                self.opening_rooms_id.remove(reply)
                print('>Leave room!')
                print('>Now you are opening room:')
                self.ShowOpeningChatRooms()
        except Exception as e:
                print('In JoinChatRoom:', e)            
    
    def ShowOpeningChatRooms(self):
        tmp = ''
        for each in self.opening_rooms_id:
            tmp += each
            tmp += ',' 
        print(tmp)
        
    def FindCorrectRoom(self, target):
        try:
            sendPacket(self.socket, ('findcorrectroom;'+target+';'+self.user_id+';').encode('utf8'))
        except Exception as e:
            print("In FindCorrectRoom:", e)
        try:
            '''cant recv ??????'''
            correct_room_id = recvPacket(self.socket).decode('utf8')
            if correct_room_id == '!ERROR':
                print('No this user!Uid was wrong!')
                return 
            self.Talking(correct_room_id)
        except Exception as e:
            print("In FindCorrectRoom:", e)
    
    def Talking(self, room_id):
        while(1):
            message=input('(input "!END" to end talk)>')
            if message == "!END":
                break
            try:
                pkg = 'pushmessage;'
                pkg += message
                pkg += ';'
                pkg += room_id
                pkg += ';'
                pkg += self.user_id
                pkg += ';'
                sendPacket(self.socket, pkg.encode('utf8'))
            except Exception as e:
                print("In PushMessages:", e)
        print('>End talk.')
        
    def Broadcast(self, message):
        pkg = 'pushmessage;'
        pkg += message
        pkg += ';'
        pkg += '-1;'
        pkg += self.user_id
        pkg += ';'
        try:
            sendPacket(self.socket, pkg.encode('utf8'))
        except Exception as e:
            print('In Broadcast', e)
        
InteractionMode()