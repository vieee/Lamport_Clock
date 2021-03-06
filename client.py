from email.utils import formatdate      #required for formating date & time
from datetime import datetime           #required to get current datetime for HTTP
from time import mktime,sleep           #required for timestamp with zone
import tkinter                          #required for GUI
from tkinter import messagebox          #required for alert box
from socket import AF_INET, socket, SOCK_STREAM     #required for socket programming
from threading import Thread            #required for multitherading
import random                           #genrate random number
import ast                              #converts a string containing a dictionary to an actual dictionary

def startTimer():
# Description
#  The function runs as a seperate thread and its job is it increment timer
#  every second and display the time continusly on the client window
# Input: NA
# Output: NA

    global clock,quitClient         #clock is an global variable; quitClient is to indicate if
                                    # a client has decided to quit
    msg_list.insert(tkinter.END,"Clock set to: "+ str(clock))     #display initial time
    msg_list.see(tkinter.END)       #set to new line
    while quitClient == False:      #timer should run until closed, hence infinite loop
        sleep(1)                    #sleep for a second before incrementing the counter
        clock = clock + 1           # increment the time counter
        try:
            logClock.delete(0,tkinter.END)      #clears the window
            #display the time on the client window continously
            logClock.insert(tkinter.END,"Clock: "+ str(clock))
        except RuntimeError:
            break

def parseHTTPresponse(Httpmsg):
# Description
    # The function parses the incoming HTTP response message from server
    # and returns the payload;
# Input:
#     Httpmsg-> HTTP encoded response message
# Output:
#     status-> HTTP response message status
#     query-> parsed payload in dictonary format

    crlf = "\r\n"           # Carriage return & Line feed for HTTP request message
    status = 0              # Status of HTTP response message initialize
    query = {}              # dictionary to hold the payload of the HTTP response
    ss = Httpmsg.split(crlf)    # split the message based on the CRLF and store into a list
    first_line = ss[0].split(" ")       # read the first line of the HTTP response (to get status)
    try:
        if first_line[1] == '200':      # if the status is 200 (OK)
            status = 200                # store the status to return

            # split the last line of payload based on delimiter && to
            # fetch all elements of the payload and store into a list
            # Ex: payload may contain: name=john&&message=hello
            # so payload will have => [name=john, message=hello]
            payload = ss[len(ss) - 1].split("&&")

            # split each element of the list payload based on '='
            # from the above example, the below dictionary query will have
            # query={'name':'john','message':'hello'}
            # Please note that if the original message contains =, blank will be sent
            for item in payload:
                left,right = item.split("=")       # split based on '='
                query.update({left:right})         # add new pair to dictionary
        else:
            status = 400        # update status (400= Bad request
    except IndexError:          # Check for Index error
        pass;                   # This exception wont occur since HTTP message is coded by us

    return status,query         # return the status and dictionary payload

def encodeHTTP(method,query):
# Description:
    # Given a dictionary of values and HTTP method(GET or POST),
    # this function encodes the query into HTTP request
# Input:
#    method-> HTTP method (POST or GET)
#    query-> dictioanry pairs of data to be sent to the server
# Output
#    HTTPmsg-> HTTP encoded message
    space = " "                     # space to delimit HTTP request
    url = "/"                       # start of the url (for POST its empty)
    host1 = "127.0.0.1:5001"        # host address (here its localhost)
    version = "HTTP/1.1"            #HTTP version
    crlf = "\r\n"                   #carriage return and line feed used for line seperator for http request
    user_agent = "python-client 1.0"     # user agent, usign python client here
    content_type = "text/plain"     # content type is plain text (no file transfer supported)

    now = datetime.now()            # get current date and time
    stamp = mktime(now.timetuple()) # convert local time to seconds since the Epoch
    # formats the above time into HTTP timestamp format
    date =  (formatdate( timeval = stamp, localtime = False, usegmt = True ))

    payload=""          #initialize payload

    # the following code converts dictionary(query) into string format as follows:
    # query={'name':'john','message':'hello'}
    # payload will have => name=john&&message=hello
    for idx, item in enumerate(query):
        if idx < len(query) - 1:
            payload = payload+item+"="+query[item]+"&&"     #add && as delimiter
        else:
            payload = payload+item+"="+query[item]      #no need of delimiter && for last line

    content_len = len(payload)      # payload length
    if method == 'GET':             # if the method is GET,
        url = url+'?'+payload       # store payload in URL

    # concatenate all HTTP headers stored above
    HTTPmsg = method + space + url + space + version + crlf
    HTTPmsg = HTTPmsg + "Host: " + host1 + crlf
    HTTPmsg = HTTPmsg + "User-Agent: " + user_agent + crlf
    HTTPmsg = HTTPmsg + "Content-Type: " + content_type + crlf
    if method == 'GET':
        # Content length is zero for GET request
        HTTPmsg = HTTPmsg + "Content-Length: " + "0" + crlf
    else:
        # payload length is the content length for POST request
        HTTPmsg = HTTPmsg + "Content-Length: " + str(content_len) + crlf
    HTTPmsg = HTTPmsg + "Date: " + date + crlf + crlf
    if method == 'POST':                #if payload is POST
        HTTPmsg = HTTPmsg + payload     # store the payload in HTTP body
    return HTTPmsg                      # return the HTTP encoded message

def send_msg(msg):
# Description:
#   Sends the message to the server
# Input:
#     msg-> HTTP Request message
# Output: NA
    global serverConnected
    try:
        sock.send(bytes(msg, "utf8"))   # send the message to server
    except ConnectionResetError:
        # This error occurs on server dserver disconnection
        msg_list.insert(tkinter.END,"Server Disconnected")
        serverConnected = False
        msg_list.see(tkinter.END)      #scrolls to the latest message
    except ConnectionAbortedError:     #server disconected
        pass

def clientList():
# Description:
#   This is a seperate thread which continously asks for client lists every 3 seconds
#   Sends the request to server for client list every 3 seconds to choose
#    from the list of clients; it has to be noted that selecting a random client
#    and sending the local time to that client is performed in recieve thread
# Input: NA
# Output: NA
    global quitClient, serverConnected

    # loop untill client has not quit
    while quitClient == False and serverConnected == True:
        # fetch client list every 3 seconds; basically what it does is to
        #     prepare itself to send local time every 3 seconds by asking for real
        #     time client list from server
        sleep(8)
        HTTPmsg = encodeHTTP("GET",{'clients':'True'})  # encode HTTP query for client list
        try:
            send_msg(HTTPmsg)                               # send query to server
        except RuntimeError:
            return

def send(event=None):
# Description:
# This is called when user enters the client name; It has 3 functions:
#     1. registers client name on the server
#     2. starts the clock thread
#     3. starts the thread to get client list to eventually send local time
# Input: NA
# Output: NA
    global clock,name,quitClient
    if quitClient == True:              # check if user has clicked on Quit
        if serverConnected == True:     # check if server is connected
            #if server is still on & user has quit, inform the server about the quit
            HTTPmsg = encodeHTTP("POST",{'quit':'True'})    #encode quit message
            send_msg(HTTPmsg)           # send the message to server
        return                          # nothing more to do, so return

    name = my_msg.get()   # read user input
    my_msg.set("")        # Clears input field.
    top.title(name)       # change the client window title
    HTTPmsg = encodeHTTP("POST",{'name':name})      #parse name into HTTP request
    send_msg(HTTPmsg)               # register the client name onto server
    msg_list.insert(tkinter.END,"Your name is stored in server as "+name+". You can send messages now.")       #display info to user
    msg_list.see(tkinter.END)       # scroll to the bottom
    send_button.config(state="disabled")    #disable send button
    entry_field.config(state="disabled")    # disable the text input box

    # start the thread to clock the time
    timer_thread = Thread(target=startTimer)
    timer_thread.start()

    # start the thread to get client list from server
    clientlist_thread = Thread(target=clientList)
    clientlist_thread.start()



def receive():
# Description:
#     This function is called as new thread which cotinously listens to server
#     and receives messaged from it untill either server quits or client quits.
#     Here, the HTTP response from the server can be any of the following:
#     1. receive remote time from other clients and adjust local time based on
#           Lampard clock
#     2. Upon geting list of active clients stored in the server,
#          send the local time to a randomly selected client
#     3. receive Server disconnection notification
#     Based on the above criteria, suitable actions are taken.
# Input: NA
# Output: NA
    global clock, quitClient, serverConnected
    while True:         # continuosly receive data from server
        try:
            msg = sock.recv(buffer).decode("utf8")      #receive HTTP response from server
            if quitClient == True or serverConnected == False:
                break       #if server or client is killed, stop the loop
            status,payload = parseHTTPresponse(msg)     # parse the HTTP response message
            try:
                sender = payload['source']      # get the remote client name sending its time
                remote_time = int(payload['time'])      #type cast the time from string to int
                msg_list.insert(tkinter.END,sender+"'s Time: "+ str(remote_time))    #display the remote time
                msg_list.insert(tkinter.END,"Local time: "+ str(clock))          # display local time
                # Lampard clock logic:
                if remote_time >= clock:        #if incoming time is greater than local time,
                    clock = remote_time + 1     # reset local time by adding 1 to remote time
                    #display new local time
                    msg_list.insert(tkinter.END,"Local clock reset to: "+ str(clock))

                    #update the local clock window
                    logClock.delete(0,tkinter.END)              #scroll to bottom
                    logClock.insert(tkinter.END,"Clock: "+ str(clock))
                else:
                    #if incoming time is lesser than local time, no time reset
                    msg_list.insert(tkinter.END,"No adjustment necessary")
                msg_list.see(tkinter.END)       #scroll to bottom
            except KeyError:        #upon getting client list, pick random client and send time
                try:
                    clist = ast.literal_eval(payload['clist'])      #converts a string containing a dictionary to an actual dictionary
                    clist.remove(name)                      # removes self from the list of clients
                    n = len(clist)                          #number of remaining clients
                    if n:
                        r = random.randint(0,n)             # selects a random client index
                        try:
                            #encode the time and soirce into HTTP
                            msg_list.insert(tkinter.END,"Remote client selected: "+clist[r])
                            msg_list.insert(tkinter.END,"Local time sent: "+str(clock))
                            HttpMsg = encodeHTTP("POST",{'destination':clist[r],'clock': str(clock)})
                            send_msg(HttpMsg)       #send the encoded message
                        except IndexError:
                            continue
                except KeyError:
                    try:        # Server disconnection notification
                        if payload['serv_quit'] == 'True':
                            serverConnected = False
                            msg_list.insert(tkinter.END,"Server disconnected; Communication not possible!")
                            msg_list.see(tkinter.END)      #scroll to latest line
                    except KeyError:
                        pass
        except ConnectionResetError:
           break

def win_close(event=None):
# Description:
#     Event handler called on the closing of window
# Input: NA
# Output: NA
    global  quitClient
    quitClient = True       #set quit to True
    send()          # call the send() method to notify server abt the disconnection
    top.quit()      # stop the main loop of tkinter GUI


if __name__ == "__main__":
# Description:
#     Execution starts from here; All globals are declared here;
#     The Tkinter GUI is initialized here
#     The concurrent thread for listening to server is also started here
# Input:
# Output:

    clock = random.randint(0,51)        #initialize the clock to any number b/w 0 & 50
    quitClient = False                  #quitClient initialized to false
    name = ""                           #local client name
    serverConnected = True              #serverConnected initialied to true

    top = tkinter.Tk()      # create a root window handler
    top.title("Client")     # set the window titlw as client; updated once the user enters name
    messages_frame = tkinter.Frame(top)         #message frame to display text on the window

    my_msg = tkinter.StringVar()  # to set and get text from tkinter.Entry (input box)
    my_msg.set("")                # set it to blank at first

    scrollbar = tkinter.Scrollbar(messages_frame)  # To navigate through past messages.
    # creates listbox to display the text entered by the user
    msg_list = tkinter.Listbox(messages_frame, height=15, width=70, yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tkinter.RIGHT, fill=tkinter.Y)      #set the scrol bar for first view

    # configure list box geometry
    msg_list.pack(side=tkinter.LEFT,expand=tkinter.YES, fill=tkinter.BOTH)
    msg_list.pack()

    logClock = tkinter.Listbox(messages_frame, height=15, width=25)
    logClock.pack(side=tkinter.BOTTOM,expand=tkinter.YES, fill=tkinter.BOTH)
    logClock.pack()

    # configures the frame geometry allowing it to expand
    messages_frame.pack(expand=tkinter.YES,fill=tkinter.BOTH)

    #Label for input box
    button_label = tkinter.Label(top, text="Enter name:")
    button_label.pack()

    # Input box for user input: we can set the input and read value off it using
    # variable 'my_msg'; also the input font color is set to red
    entry_field = tkinter.Entry(top, textvariable=my_msg, foreground="Red")

    # calls the send() method on pressing enter
    entry_field.bind("<Return>", send)
    entry_field.pack()

    # button to send the message; calls send() method
    send_button = tkinter.Button(top, text="Send", command=send)
    send_button.pack()

    # button to quit; calls win
    quit_button = tkinter.Button(top, text="Quit", command=win_close)
    quit_button.pack()

    # on closing the window; call the win_close() function
    top.protocol("WM_DELETE_WINDOW", win_close)

    # prompt to the user to register the client name on the server
    msg_list.insert(tkinter.END, "Enter your name:")
    msg_list.see(tkinter.END)       #srcoll tp the latest message

    host = "127.0.0.1"          # server IP address; here its localhost
    port = 5002                 # port number of the server (hardcoded)
    buffer = 1024               # buffer size
    addr = (host, port)         # IP address-port tuple
    sock = socket(AF_INET, SOCK_STREAM)     # creates a socket for TCP connection
    try:
        sock.connect(addr)                  # connects to the localhost server with its port
        # starts new thread to listen to the server for messages contnously
        receive_thread = Thread(target=receive)
        receive_thread.start()
        # start the GUI main loop
        tkinter.mainloop()
    except ConnectionRefusedError:      # if server connection failed
        top.destroy()                   # destroy the UI

        # display message that no server is active
        serv_msg = "Server not listening. Please run 'server.py' first and try again"
        tkinter.messagebox.showinfo("Message",serv_msg)     #alert box
        print(serv_msg)