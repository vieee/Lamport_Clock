from email.utils import formatdate          #required for formating date & time
from datetime import datetime               #required to get current datetime for HTTP
from time import mktime                     #required for timestamp with zone
#required for socket programming
from socket import AF_INET, socket, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from threading import Thread                #required for multitherading
import tkinter                              #required for GUI


def displayHttpMessage(name="",HttpMsg="",type=""):
# Description:
#   Listbox of Tkinter doesnt recognize the /n in the string. This function
#   takes in source client name and the HTTP message itself; formats it and displays
#   it on the Listbox of UI
# Input:
#     name-> name of the source client of the HTTP message
# Output: NA

    if type == "1":
        disp_msg = "HTTP request from client-"+name+":"
    elif type == "2":
        disp_msg = "Server's HTTP response to "+name+":"
    else:
        disp_msg = "Server's broadcast HTTP response:"

    msg_list.insert(tkinter.END, "")        # New line before every HTTP message
    # Message before display
    # msg_list.insert(tkinter.END,"HTTP request from client- "+name+":")
    msg_list.insert(tkinter.END,disp_msg)
    httpmsg_list = HttpMsg.split("\r\n")    # split the HTTP mesage basaed on CRLF
    # display each line in the HTTP message in new line
    for i in httpmsg_list:
        msg_list.insert(tkinter.END,i)
    msg_list.see(tkinter.END)               # scroll the listbox to the latest line

def encodeHTTPresponse(status,query):
# Description:
#     The server sends messages to clients in the HTTP response format.
#     This function takes the status (200 or 400) and a dictionary query(payload) and
#     forms a HTTP response message
# Input:
#     status-> status of the response (200 OK; 400 - Bad request ie; when invalid client selected)
# Output:
#     Httpmsg-> HTTP encoded message

    space = " "                         # space to be used in the response message
    host1 = "127.0.0.1:5001"            # server address
    version = "HTTP/1.1"                # HTTP version
    crlf = "\r\n"                       #carriage return and line feed used for line seperator for http request
    user_agent = "python-server 1.0"    # user agent is python here
    content_type = "text/plain"         # # content type is plain text (no file transfer supported)

    if status == 200:                   # status message based on status
        status_msg = 'OK'               # OK status
    else:
        status_msg = 'Bad Request'      # Bad request ie; when invalid client selected

    now = datetime.now()                # get current date and time
    stamp = mktime(now.timetuple())     # convert local time to seconds since the Epoch

    # formats the above time into HTTP timestamp format
    date =  (formatdate( timeval = stamp, localtime = False, usegmt = True ))
    payload=""                          #initialize payload
    if status == 200:                   # on successfull response
        # format the HTTP response payload into the following format:
        # EX: query will have {'name':'john,'message':'hello'}
        # payload = name=John&&message=hello
        for idx, item in enumerate(query):      # for each item in the query
            if idx < len(query) - 1:
                payload = payload+item+"="+query[item]+"&&"     # concatenate the dictioary items
            else:
                payload = payload+item+"="+query[item]          # no need && for last item

    # concatenate the whole http response
    content_len = len(payload)
    HTTPmsg = version + space + str(status) + space + status_msg + crlf
    HTTPmsg = HTTPmsg + "Host: " + host1 + crlf
    HTTPmsg = HTTPmsg + "User-Agent: " + user_agent + crlf
    HTTPmsg = HTTPmsg + "Content-Type: " + content_type + crlf
    HTTPmsg = HTTPmsg + "Content-Length: " + str(content_len) + crlf
    HTTPmsg = HTTPmsg + "Date: " + date + crlf + crlf
    if status == 200:                   # payload only present if status is OK
        HTTPmsg = HTTPmsg + payload
    return HTTPmsg                      # return the HTTP response message

def parseHTTPrequest(Httpmsg):
# Description:
#   The clients communicates with the server via HTTP request messages. So, in order to
#     get the destination name, delivery preference and the actual message. server has to
#     parse it
# Input:
#     Httpmsg-> HTTP request message from the client
# Output:
#     query->  dictionary containing the payload

    crlf = "\r\n"                   # carriage return and line feed used for line seperator for http request
    query = {}                      # intialize the query
    ss = Httpmsg.split(crlf)        # split http message based on CRLF
    first_line = ss[0].split(" ")   # get the method name (POST/GET) from the first line
    if first_line[0] == 'POST':     # get the payload from the message body if POST
        payload = ss[len(ss) - 1].split("&&")
    else:                           # if GET reuest,
        temp = first_line[1].split("?")         # get query from URL after the ? symbol
        payload = temp[1].split("&&")           # split the message elements on &&

    # formulate the above split items into dictionary pair
    for item in payload:
        payload_items = item.split("=")         # split based on = symbol
        query.update({payload_items[0]:payload_items[1]})   # add items to dictionary
    return query                                # return the payload dictionary

def disconnect():
# Description:
#   This function is called upon 'disconnect' button click
#   This function notifies all its clients about its own disconnection before and
#   then closes the client sockets and server socket
# Input: NA
# Output: NA
    global server_close     # server close flag inidicates the server status in the program
    server_close = True     # set the flag to True
    if clients:             # if ther are still active clients, broadcast server disconnection
        server_disconnected_broadcast()     # send server disconnection notification
    print("disconnected")
    msg_list.insert(tkinter.END,"Disconnected")     #display on the server GUI
    msg_list.see(tkinter.END)                       # scroll to latest text
    discon_button.config(state="disabled")          # disable the 'disconnect button
    for conn in clients:                            # close all the client sockets
        conn.close()
    serverSocket.close()                            # close the server socket
    top.quit()                                      # stop the GUI

def connect_to_client():
# Description:
#     This functions executes as a seperate thread off the main program to
#      continoulsy listen to its port for client connections.
#      It also starts a new thread per client to receive data from it seperately
# Input: NA
# Output: NA
    while True:         #continously listens to the port untill disconnected
        try:
            # welcome socket connection
            client, client_address = serverSocket.accept()
            if server_close == True:    # if server is disconnected, exit the loop
                break
            # start the thread to recieve data from clients
            Thread(target=listen_to_client, args=(client, client_address)).start()
        except OSError:
            break


def listen_to_client(conn, addr):
# Description:
#   Receives HTTP requests from clietns, parse them and display them on the server window
#   This function executes as a seperate thread for every client. It has 3 operations:
#   1. Handles client disconnections
#   2. Message delivery & broadcast
#   3. Send active client list to reuest clients
# Input:
#   conn-> server socket (welcome socket) handle
#   addr-> client address
# Output: NA

    HTTPmsg = conn.recv(buffer).decode("utf8")      #receive HTTP message
    query = parseHTTPrequest(HTTPmsg)               # parse the HTTP request
    name = query['name']                            # the first message from client is the name
    clients[conn] = name                            # store the name in a global dictionary
    # displayHttpMessage(name, str(HTTPmsg))          # display the HTTP message on the server window
    # delete the active client list and update the list with new clients
    active_list.delete(0,tkinter.END)
    active_list.insert(tkinter.END,"Active Clients")    # heading for active clients
    for item in clients:                                # add the clients to List box
        active_list.insert(tkinter.END,clients[item])
    msg = "%s has joined" %name
    msg_list.insert(tkinter.END,"")                  # New line
    msg_list.insert(tkinter.END,msg)                 # display msg once client joins
    msg_list.see(tkinter.END)
    # broadcast(msg,'2','server')                      # broadcast abt new client joining

    # once the client name is stored, this thread contiously listens to the client for data
    while True:
        try:
            HTTPmsg = conn.recv(buffer)         # receive data from client
            if server_close == True:            # if server is disconnected, stop listening
                break
            displayHttpMessage(name, str(HTTPmsg,"utf8"),"1")   # display the HTTP message on server window
            query = parseHTTPrequest(str(HTTPmsg,"utf8"))   # parse the HTTP request
            try:
                if query['quit'] == 'True':             # handles client disconection
                    conn.close()                        # close the server socket
                    del clients[conn]                   # remove the name from the client dictionary
                    active_list.delete(0,tkinter.END)   # update the active list window
                    active_list.insert(tkinter.END,"Active Clients")
                    for item in clients:                # add all active clients to active window
                        active_list.insert(tkinter.END,clients[item])
                    quit_msg = "%s disconnected" % name
                    msg_list.insert(tkinter.END,"")         # new line
                    msg_list.insert(tkinter.END, quit_msg)  # display the mesage abt client disconenction
                    msg_list.see(tkinter.END)
                    # broadcast abt disconnection to all remaining clients
                    broadcast(quit_msg,'2','server')
                    break
            except KeyError:
                try:
                    if query['clock']:
                        send_time(query['clock'],query['destination'],name)
                except KeyError:
                    try:       # sending messages
                        if query['delv'] == '1':        # delivery method is 1-1
                            # send msg to destination client
                            send_message(query['message'],query['delv'],query['destination'],name)
                        else:
                            # if deilivery method is 1-N, broadcast to all clients
                            broadcast(query['message'],query['delv'],name)
                    except KeyError:
                        try:    # sending client list to request clients
                            if query['clients'] == 'True':
                                send_clientlist(name)
                        except KeyError:
                            pass;
        except ConnectionResetError:          # on client socket disconnection
            break
        except ConnectionAbortedError:
            break

def send_clientlist(dest=""):
# Description:
    # Sends the list of active clients to the client in "dest"
# Input:
#    dest: name of the client that reuest the client list
# Output: NA

    clist = list(clients.values())          # get the client names from the dictionary of clients
    query = {'clist': str(clist)}            # form the payload for HTTP with keyword 'query'
    for sock in clients:                    # find the client that reuest the list ie; find "dest"
        if clients[sock] == dest:           # if client found,
            HTTPresponse = encodeHTTPresponse(200,query)    # encode the 'query' into HTTP response
            sock.send(bytes(HTTPresponse,"utf8"))           # send the HTTP encoded client list
            displayHttpMessage(dest,HTTPresponse,"2")                 #display server response on window
            break

def send_time(time="",dest="",source=""):
# Description:
#   sends time frm one client to another
# Input:
#    time-> local time of client in 'source'
#    dest-> destination client name to which time has to be sent
#    source-> source client name who is sending its time
# Output:  NA
    client_valid = False        # flag to check if the input client is valid
    # prepare the query which will be encoded into HTTP message
    query = {'time':time,'source':source}
    # loop through the client list and send message to the destination only
    for sock in clients:
        if clients[sock] == dest:
            client_valid = True                             # set the valid flag if client is found
            HTTPresponse = encodeHTTPresponse(200,query)    # encode the message into HTTP
            sock.send(bytes(HTTPresponse,"utf8"))           # send message to clients
            break
    if client_valid == False:                               # if no destination found in client list
        # encode a HTTP response back to the source with 400 status
        HTTPresponse = encodeHTTPresponse(400,{})
        for sock in clients:
            if clients[sock] == source:                     # look up for the source
                sock.send(bytes(HTTPresponse,"utf8"))       # send the 400 Status response
                break
    if HTTPresponse:
        msg_list.see(tkinter.END)
        displayHttpMessage(dest,HTTPresponse,"2")                 #display server response on window


def send_message(message,delv,dest="",source=""):
# Description:
#   send HTTP message to destination. This is called for 1-1 delivery method
# Input:
#     delv-> delivery method preference
#     dest-> target client
#     source-> source of the messsage
# Output:  NA
    client_valid = False        # flag to check if the input client is valid
    # prepare the query which will be encoded into HTTP message
    query = {'message':message,'delv':delv,'dest':dest,'source':source}
    # loop through the client list and send message to the destination only
    for sock in clients:
        if clients[sock] == dest:
            client_valid = True                             # set the valid flag if client is found
            HTTPresponse = encodeHTTPresponse(200,query)    # encode the message into HTTP
            sock.send(bytes(HTTPresponse,"utf8"))           # send message to clients
            break
    if client_valid == False:                               # if no destination found in client list
        # encode a HTTP response back to the source with 400 status
        HTTPresponse = encodeHTTPresponse(400,{})
        for sock in clients:
            if clients[sock] == source:                     # look up for the source
                sock.send(bytes(HTTPresponse,"utf8"))       # send the 400 Status response
                break
    if HTTPresponse:
        msg_list.see(tkinter.END)
        displayHttpMessage(dest,HTTPresponse,"2")                 #display server response on window

def broadcast(msg, delv, source=""):
# Description:
#   this is called when delivery preference is 1-N
# Input:
#   msg-> actual message to be broadcast
#   delv-> delivery preference
#   source-> source of the message
# Output: NA
#     formulate the dictionary to be encoded into HTTP response
    query = {'message':msg,'delv':delv,'source':source}
    HTTPresponse = encodeHTTPresponse(200,query)       # encode msg into http response
    for sock in clients:
        sock.send(bytes(HTTPresponse,"utf8"))          # send the http response to clients
    displayHttpMessage("",HTTPresponse,"3")                 #display server response on window

def server_disconnected_broadcast():
# Description:
#   this is called only when server is disconnected; and the same has to be notified to all
#     active clients
# Input: NA
# Output: NA
#     formulate the dictionary to be sent as notificaton abt server disconnection
    query = {'serv_quit':'True','delv':'2','source':'server'}
    HTTPresponse = encodeHTTPresponse(200,query)        # encode HTTP response
    for sock in clients:
        sock.send(bytes(HTTPresponse,"utf8"))           # send the notification to all clietns


if __name__ == "__main__":
# Description:
#   gloabal declarations, server socket connection and GUI initializations are done here
#   Also, the thread to listen to incoming client connections starts here

    top = tkinter.Tk()          # create a root window handler
    top.title("Server")         # set the window titlw as server; updated once the user enters name

    messages_frame = tkinter.Frame(top)     #message frame to display text on the window
    scrollbar = tkinter.Scrollbar(messages_frame)  # to navigate through past messages.
    # Listbox will contain the messages.
    msg_list = tkinter.Listbox(messages_frame, height=15, width=50, yscrollcommand=scrollbar.set)
    # this is division in the server window to show the live client list
    active_list = tkinter.Listbox(messages_frame, height=15, width=25, yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tkinter.RIGHT, fill=tkinter.Y)      #scroll bar for clint lists
    msg_list.pack(side=tkinter.LEFT,expand=tkinter.YES,fill=tkinter.BOTH)
    msg_list.pack()
    # configure the geometry of the client list window
    active_list.pack(side=tkinter.BOTTOM,expand=tkinter.YES, fill=tkinter.BOTH)
    active_list.pack()
    messages_frame.pack(expand=tkinter.YES,fill=tkinter.BOTH)

    # intialize clients and address dictionaries
    clients = {}
    # addresses = {}

    host = "127.0.0.1"      # server IP address; here its localhost
    port = 5002             # port number of the server (hardcoded)
    buffer = 1024           # buffer size
    addr = (host, port)     # IP address-port tuple
    server_close = False    # initialize the server disconnection flag
    #Welcome socket--- Common socket for all clients
    serverSocket = socket(AF_INET, SOCK_STREAM)     # creates a socket for TCP connection
    # makes the server port reusable
    serverSocket.setsockopt(SOL_SOCKET,SO_REUSEADDR,1)
    serverSocket.bind(addr)             #bind the socket with the above port, localhost

    # disconnect button
    discon_button = tkinter.Button(top, text="Disconnect", command=disconnect)
    discon_button.pack()
    # handler for window closing
    top.protocol("WM_DELETE_WINDOW", disconnect)

    serverSocket.listen(3)  # Listens for 3 connections at max.

    # set the inital mesages on the window
    msg_list.insert(tkinter.END,"Server listening...")
    active_list.insert(tkinter.END,"Active Clients")

    # start thread for listening on its port for incoming connections
    accept_thread = Thread(target=connect_to_client)
    accept_thread.start()       # start the thread
    tkinter.mainloop()          # GUI loop  starts here
    serverSocket.close()        # once the server gets disconnected; this statement executes
