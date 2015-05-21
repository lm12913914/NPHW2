import socket
import queue
import threading
import select
import atexit
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

def exit_handler():
    print('My application is ending!')
    
atexit.register(exit_handler)

class MyPackage:
    def __init__(self):
        self.pkg_from = ""
        self.pkg_to = ""
        self.content = ""
    def __enter__(self):
        return self
    
    def __exit__(self, type, value, traceback):
        pass

class User:
    def __init__(self, uid, uname, upwd):
        self.user_id = uid
        self.user_name = uname
        self.user_pwd = upwd
        self.user_socket = self.SetSocket()
        self.user_status = 'off'
        self.recv_message_q = queue.Queue()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        pass
        
    def SetSocket(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR, 1)
        s.settimeout(1)
        return s
        
class ChatRoom:
    '''write each new message to list every time'''
    def __init__(self, room_id, member_ids):
        self.room_id = room_id
        self.member_count = len(member_ids)
        self.member_list = member_ids
#        self.member_list = []
#        self.CreateMemberList(mebmer_ids)
        self.message_log_file = 'chatrooms/'+str(room_id)+'.txt'
        self.message_log_list = []
        self.message_list = []
        try:
            with open(self.message_log_file) as file:
                for line in file.read().splitlines():
                    self.message_log_list.append(line)
        except:
            with open(self.message_log_file, 'w') as file:
                for line in self.message_log_list:
                    file.write(line)
#            print('In class chat_room: __init__ : file %s not found'%self.message_log_file)

    def __enter__(self):
        return self
    
    def __exit__(self, type, value, traceback):
        with open(self.message_log_file, 'w') as file:
            for each in self.message_log_list:
                file.write(each+'\n')
    
#    def CreateMemberList(self, ids):
#        with open('userlist.txt') as file:
#            for line in file.read().splitlines():
#                user_id, user_name, user_pwd = line.split(':')
#                for i in range(len(ids)):
#                    if user_id == ids[i]: #this user is in the room 
#                        self.member_list.append(User(user_id, user_name, user_pwd))
    
    def NewMessage(self, msg):
        self.message_list.append(msg)

    def AddMember(self, user_id):
        self.member_list.append(user_id)

    def DelMember(self, user_id):
        self.member_list.remove(user_id)


class StartServer:
    def __init__(self):
        self.user_list = []
        self.ReadUserList()
        self.room_list = []
        self.ReadRooms()
        '''broadcastroom wont show in room_list'''
        self.InitBroadcastRoom()
        self.socket_list = []
        self.socket_list.append(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
        myThread = threading.Thread(target=self.ReceivingConnections)
        myThread.setDaemon(True)
        myThread.start()
        while(1):
            data, index = self.WaitMessages()
            pkg_content = data.decode('utf8').split(';')
            '''new'''
            if '' in pkg_content:
                pkg_content.remove('')
            '''new'''
            self.ReplyJudge(pkg_content, index)

    
    def ReadUserList(self):
        with open('userlist.txt') as file:
            for line in file.read().splitlines():
                user_id, user_name, user_pwd = line.split(':')
                self.user_list.append(User(user_id, user_name, user_pwd))
    
    def InitBroadcastRoom(self):
        all_user_ids_list = []
        for each in self.user_list:
            all_user_ids_list.append(each.user_id)
        self.broadcast_room = ChatRoom(-1, all_user_ids_list)
                
    def ReceivingConnections(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR, 1)  
        s.bind(('127.0.0.1', 12345))  
        s.listen(30)
        while(1):
            conn, address = s.accept()
            self.socket_list.append(conn)
        s.close()

    def WaitMessages(self) :
        '''
        Block until any message, return (message, index)
        '''
        get_one = False
        while (not get_one):
            readable = select.select(self.socket_list,[],[], 0)[0]
            if readable != []:
                get_one = True
        return recvPacket(readable[0]), self.socket_list.index(readable[0])

    def ReplyJudge(self, pkg_content, socket_index):
        if pkg_content[0] == 'login':
            '''if login success, status="on", user_socket=this socket'''
            user_id='-1'
            pkg =''
            qsize = 0
            for each in self.user_list:
                if each.user_name==pkg_content[1] and each.user_pwd==pkg_content[2]:
                    user_id = each.user_id
                    each.user_status = 'on'
                    each.user_socket = self.socket_list[socket_index]
                    qsize = each.recv_message_q.qsize()                    
                    for i in range(qsize):
                        msg, speaker = each.recv_message_q.get()
                        pkg += msg
                        pkg += ':'
                        pkg += self.user_list[int(speaker)].user_name
                        pkg += ';'        
            try:
                sendPacket(self.socket_list[socket_index], user_id.encode('utf_8'))
                sendPacket(self.socket_list[socket_index], str(qsize).encode('utf8'))
            except Exception as e:
                print('In ReplyJudge:In login', e)
            if not(qsize==0):
                sendPacket(self.socket_list[socket_index], pkg.encode('utf8'))
        elif pkg_content[0] == 'logout':
            for each in self.user_list:
                if each.user_id == pkg_content[1]:
                    each.user_status = 'off'
                    each.user_socket = None        
        elif pkg_content[0] == 'listuser':
            pkg =''
            for each in self.user_list:
                pkg += each.user_id
                pkg += ':'
                pkg += each.user_name
                pkg += ';'
            try:
                sendPacket(self.socket_list[socket_index], pkg.encode('utf8'))
            except Exception as e:
                print('In ReplyJudge:In listuser', e)
                
        elif pkg_content[0] == 'listonlineuser':
            pkg =''
            for each in self.user_list:
                if each.user_status == 'on':
                    pkg += each.user_id
                    pkg += ':'
                    pkg += each.user_name
                    pkg += ';'
            try:
                sendPacket(self.socket_list[socket_index], pkg.encode('utf8'))
            except Exception as e:
                print('In ReplyJudge:In listonelineuser', e)
        
        elif pkg_content[0] == 'listchatroom':
            pkg=''
            for each in self.room_list:
                pkg += str(each.room_id)
                pkg += ':'
                for id in each.member_list:
                    pkg += self.user_list[int(id)].user_name
                    pkg += ':'
                pkg += ';'
            try:
                sendPacket(self.socket_list[socket_index], pkg.encode('utf8'))
            except Exception as e:
                print('In ReplyJudge:In listcahtroom', e)
        
        elif pkg_content[0] == 'joinchatroom':
            '''check if the room exist'''
            room_id = int(pkg_content[1])
            pkg=''
            if room_id<0 or room_id>=len(self.room_list): #room not exist
                try:
                    sendPacket(self.socket_list[socket_index], pkg.encode('utf8'))
                except Exception as e:
                    print('In replyJudge:In joinchatroom:', e)    
            else:
                pkg += pkg_content[1]
                self.JoinChatRoom(pkg_content[1], pkg_content[2])
                try:
                    sendPacket(self.socket_list[socket_index], pkg.encode('utf8'))
                except Exception as e:
                    print('In replyJudge:In joinchatroom', e)  
                        
        elif pkg_content[0] == 'leavechatroom':
            '''check if the room exist and user is in the room'''
            room_id = int(pkg_content[1])
            pkg=''
            if room_id<0 or room_id>=len(self.room_list): #room not exist
                try:
                    sendPacket(self.socket_list[socket_index], pkg.encode('utf8'))
                except Exception as e:
                    print('In replyJudge:In joinchatroom:', e) 
            else:
                pkg += pkg_content[1]
                self.LeaveChatRoom(pkg_content[1], pkg_content[2])
                try:
                    sendPacket(self.socket_list[socket_index], pkg.encode('utf8'))
                except Exception as e:
                    print('In replyJudge:In joinchatroom', e)  
        elif pkg_content[0] == 'findcorrectroom':
            '''if only-2-user room not exist, create one'''
                
            room_exist = False
            room_id = '!ERROR'
            if int(pkg_content[1])>=len(self.user_list):
                try:
                    sendPacket(self.socket_list[socket_index], room_id.encode('utf8'))
                    return
                except Exception as e:
                    print("In replyJudge:In findcorrectroom", e)
            for room in self.room_list:
                if [pkg_content[1], pkg_content[2]] == room.member_list:
                    room_exist = True
                    room_id = str(self.room_list.index(room))
                elif [pkg_content[2], pkg_content[1]] == room.member_list:
                    room_exist = True
                    room_id = str(self.room_list.index(room))
            if not room_exist:
                members_id = pkg_content[2], pkg_content[1]
                self.CreateRoom(members_id)
                room_id = str(len(self.room_list)-1)
            try:
                sendPacket(self.socket_list[socket_index], room_id.encode('utf8'))
            except Exception as e:
                print("In replyJudge:In findcorrectroom", e)   
        elif pkg_content[0] == 'pushmessage':
            self.SpeakInRoom(pkg_content[1], pkg_content[2], pkg_content[3])
        else:
            print('Comman not found')
            return     
        
    def ReadRooms(self):
        with open('chatroomlist.txt') as file:
            for line in file.read().splitlines():
                room_contents = line.split(':')                
                room_id = room_contents[0]
                room_member_count = room_contents[1]
                room_member_ids = []
                for i in range(int(room_member_count)):
                    room_member_ids.append(room_contents[2+i]) 
                self.room_list.append(ChatRoom(room_id, room_member_ids))
#                print(self.room_list)
        
    def JoinChatRoom(self, room_id, user_id):
        self.room_list[int(room_id)].AddMember(user_id)
        
    def LeaveChatRoom(self, room_id, user_id):
        self.room_list[int(room_id)].DelMember(user_id)
        
    def CreateRoom(self, members_id):
        self.room_list.append(ChatRoom(len(self.room_list), members_id))
        
    def SpeakInRoom(self, message, room_id, speaker_id):
        if room_id == '-1':
            for each in self.broadcast_room.member_list:
                if not (speaker_id==each):
                    self.user_list[int(each)].recv_message_q.put((message, speaker_id))
        else:
            for each in self.room_list[int(room_id)].member_list:
                if not (speaker_id==each):
                    self.user_list[int(each)].recv_message_q.put((message, speaker_id))

StartServer()