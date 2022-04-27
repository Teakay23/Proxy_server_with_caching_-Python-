import socket
import threading
import time
import sys
import os

blacklist = []

def start(portNum):
    try:
        print("Listening for connection.")
        main_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        main_socket.bind(('', portNum))

    
        main_socket.listen(5)

        while 1:
            connection, address = main_socket.accept()
            print("Received from", address[0], "at port", address[1])
            connectionThread = threading.Thread(target=readRequest, args=(connection, address,))
            connectionThread.start()

        main_socket.close()

    except KeyboardInterrupt:
        print("Closing server.")
        sys.exit()


def readRequest(connection, address):
    if address[0] in blacklist:
        print("Requested IP is blacklisted by Admin.")
        connection.close()
        return

    receivedRequest = connection.recv(4096)
    header = receivedRequest.split(b'\n')[0]
    link = header.split(b' ')[1]
    connect_or_get = receivedRequest.split(b' ')[0]
    file = receivedRequest.split(b' ')[1]

    if link.find(b'://') != -1:
        link = link[link.find(b'://') + 3:]

    if link.find(b':') == -1 or (link.find(b'/') != -1 and link.find(b'/') < link.find(b':')):
        requestPort = 80 # default
        if link.find(b'/') != -1:
            requestServer = link[:link.find(b'/')]
        else:
            requestServer = link
    else:
        if link.find(b'/') != -1:
            requestPort = int( (link[link.find(b':')+1:])[:link.find(b'/') - link.find(b':') - 1] )
        else:
            requestPort = int( (link[link.find(b':')+1:])[:len(link) - link.find(b':') - 1] )
        
        requestServer = link[:link.find(b':')]

    print("port:", requestPort, "\nrequestServer:", str(requestServer))

    if requestServer.decode("utf-8") in blacklist:
        print("Requested website is blacklisted.")
        connection.close()
        return

    if connect_or_get == b'CONNECT':
        print("Connect request")
        connect_request(requestServer, requestPort, connection, receivedRequest, address, file)
    else:
        print("Get request")
        get_request(requestServer, requestPort, connection, receivedRequest, address, file)


def get_request(requestServer, requestPort, connection, receivedRequest, address, file):
    file = file.replace(b".", b"_").replace(b"http://", b"_").replace(b"/", b"")

    try:
        print("Searching for: ", file)

        THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
        my_file = os.path.join(THIS_FOLDER, 'cache\\' + str(file))
        file_handler = open(my_file, 'rb')

        print("Cache Hit")
        cached_material = file_handler.readlines()
        file_handler.close()
        # connection.send("HTTP/1.0 200 OK\r\n".encode('utf-8'))            
        # connection.send("Content-Type:text/html\r\n".encode('utf-8'))
        time.sleep(1)
        
        for line in cached_material:
            connection.send(line)
        
        print("Request of client " + str(address) + " completed. ")
        connection.close()

    except FileNotFoundError as e:
        print(e)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((requestServer, requestPort))
            s.send(receivedRequest)

            print("Forwarding request from ", address, " to ", requestServer)
            file_object = s.makefile('wb', 0)
            file_object.write(b"GET " + b"http://" + file + b" HTTP/1.0\n\n")
            file_object = s.makefile('rb', 0)
            buff = file_object.readlines()

            print("creating cache file")
            my_file = os.path.join(THIS_FOLDER, 'cache\\' + str(file))
            temp_file = open(my_file, "wb+")

            for line in buff:
                temp_file.write(line)
                connection.send(line)

            print("cache file created")

            print("Request of client " + str(address) + " completed. ")
            s.close()
            connection.close()

        except Exception as e:
            print("Error: forward request..." + str(e))
            return


def connect_request(requestServer, requestPort, connection, receivedRequest, address, file):
    file = file.replace(b".", b"_").replace(b"http://", b"_").replace(b"/", b"")

    try:
        print("Searching for: ", file)

        THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
        my_file = os.path.join(THIS_FOLDER, 'cache\\' + str(file))
        file_handler = open(my_file, 'rb')

        print("Cache Hit")
        cached_material = file_handler.readlines()
        file_handler.close()
        # connection.send("HTTP/1.0 200 OK\r\n".encode('utf-8'))            
        # connection.send("Content-Type:text/html\r\n".encode('utf-8'))
        time.sleep(1)
        
        for line in cached_material:
            connection.send(line)
        
        print("Request of client " + str(address) + " completed. ")
        connection.close()

    except:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((requestServer, requestPort))
            
            reply = "HTTP/1.0 200 Connection established\r\n"
            reply += "Proxy-agent: K190181_K191449\r\n"
            reply += "\r\n"
            connection.sendall(reply.encode())

        except socket.error as err:
            pass
            # print(self.getTimeStampp() + "  Error: No Cache Hit in HTTPS because " + str(err))
            # self.write_log(self.getTimeStampp() + "  Error: No Cache Hit in HTTPS beacuse" + str(err))

        connection.setblocking(0)
        s.setblocking(0)
        print("HTTPS Connection Established")
        while True:
            try:
                receivedRequest = connection.recv(4096)
                s.sendall(receivedRequest)
            except socket.error as err:
                pass

            try:
                reply = s.recv(4096)
                connection.sendall(reply)
            except socket.error as e:
                pass


if __name__ == "__main__":
    THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
    my_file = os.path.join(THIS_FOLDER, 'blacklist.txt')
    
    try:
        blacklist_file = open(my_file, 'r')
    except FileNotFoundError:
        blacklist_file = open(my_file, 'w+')

    lines = blacklist_file.readlines()

    for line in lines:
        if line != '\n':
            line = line.replace('\n', '')
            blacklist.append(line)

    blacklist_file.close()

    while 1:
        os.system("cls")
        print("Enter a number to select:\n")
        print("1. Filter content (Add Site/IP and websites to blacklist)")
        print("2. Allow content (Remove Site/IP and websites from blacklist)")
        print("3. Start proxy server.")
        print("4. Exit")
        inp = int(input("\nSelection: "))

        if inp == 1:
            blackSite = input("Enter site/IP:port to blacklist: ")
            blacklist.append(blackSite)

            THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
            my_file = os.path.join(THIS_FOLDER, 'blacklist.txt')
            blacklist_file = open(my_file, 'w')

            for site in blacklist:
                blacklist_file.write(site + '\n')

            blacklist_file.close()

            print("Site/IP added to blacklist. Press Enter to continue.")
            input()

        elif inp == 2:
            while 1:
                os.system("cls")
                print("List of blacklisted content:")

                for i,j in enumerate(blacklist):
                    print(str(i+1) + ".", j)

                inp2 = input("\nEnter a number to remove website/IP, enter 'b' to go back: ")
                if inp2 == 'b':
                    break

                try:
                    blacklist.remove(blacklist[int(inp2)-1])
                except:
                    print("Invalid input. Press Enter to try again.")
                    input()
                    continue

                THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
                my_file = os.path.join(THIS_FOLDER, 'blacklist.txt')
                blacklist_file = open(my_file, 'w')

                for site in blacklist:
                    blacklist_file.write(site + '\n')

                blacklist_file.close()
                
                print("Site/IP removed from blacklist. Press Enter to continue.")
                input()
                break

        elif inp == 3:
            start(6543)

        elif inp == 4:
            break

        else:
            print("Invalid input. Press Enter to try again.")
            input()