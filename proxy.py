import socket
import threading
import time
import sys
import os
import glob

blacklist = []
priorityQueue = []
roundRobinQueue = []
roundRobinDictionary = dict()
schedulingMode = 'round_robin'
visitThreshold = 3

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
    global priorityQueue, roundRobinDictionary, roundRobinQueue

    file = file.replace(b".", b"_").replace(b"http://", b"_").replace(b"/", b"")

    try:
        print("Searching for: ", file)

        THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
        my_file = os.path.join(THIS_FOLDER, 'cache\\' + str(file))
        file_handler = open(my_file, 'rb')

        print("Cache Hit")

        if schedulingMode == 'fifo':
            insertion = str(file)
            priorityQueue.remove(insertion)
            priorityQueue.append(insertion)

            fifo_file_path = os.path.join(THIS_FOLDER, 'fifo.txt')
            fifo_file = open(fifo_file_path, 'w')

            for site in priorityQueue:
                fifo_file.write(site + '\n')

            fifo_file.close()

        if schedulingMode == 'round_robin':
            if str(file) in roundRobinDictionary.keys():
                roundRobinDictionary[str(file)] += 1
            else:
                roundRobinDictionary[str(file)] = 1

            roundRobinQueue.remove(str(file))
            roundRobinQueue.append(str(file))

            roundRobin_file_path = os.path.join(THIS_FOLDER, 'round_robin.txt')
            roudnRobin_file = open(roundRobin_file_path, 'w')

            for site in roundRobinQueue:
                roudnRobin_file.write(site + '\n')

            roudnRobin_file.close()

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

            cacheFlag = False

            if schedulingMode == 'fifo':
                if len(priorityQueue) >= 10:
                    removal = priorityQueue.pop(0)

                    delete_file = os.path.join(THIS_FOLDER, 'cache\\' + removal)

                    if os.path.exists(delete_file):
                        os.remove(delete_file)

                insertion = str(file)
                priorityQueue.append(insertion)

                fifo_file_path = os.path.join(THIS_FOLDER, 'fifo.txt')
                fifo_file = open(fifo_file_path, 'w')

                for site in priorityQueue:
                    fifo_file.write(site + '\n')

                fifo_file.close()

                cacheFlag = True

            if schedulingMode == 'round_robin':
                strFile = str(file)
                if strFile in roundRobinDictionary.keys():
                    roundRobinDictionary[strFile] += 1
                else:
                    roundRobinDictionary[strFile] = 1

                if roundRobinDictionary[strFile] > visitThreshold:
                    if len(roundRobinQueue) >= 10:
                        removal = roundRobinQueue.pop(0)

                        delete_file = os.path.join(THIS_FOLDER, 'cache\\' + removal)

                        if os.path.exists(delete_file):
                            os.remove(delete_file)

                    insertion = str(file)
                    roundRobinQueue.append(insertion)

                    roundRobin_file_path = os.path.join(THIS_FOLDER, 'round_robin.txt')
                    roundRobin_file = open(roundRobin_file_path, 'w')

                    for site in roundRobinQueue:
                        roundRobin_file.write(site + '\n')

                    roundRobin_file.close()

                    cacheFlag = True

            if cacheFlag == True:
                print("creating cache file")
                my_file = os.path.join(THIS_FOLDER, 'cache\\' + str(file))
                temp_file = open(my_file, "wb+")

            for line in buff:
                if cacheFlag == True:
                    temp_file.write(line)
                connection.send(line)
            
            if cacheFlag == True:
                print("cache file created")

            print("Request of client " + str(address) + " completed. ")
            s.close()
            connection.close()

        except Exception as e:
            print("Error: forward request..." + str(e))
            return


def connect_request(requestServer, requestPort, connection, receivedRequest, address, file):
    global priorityQueue, roundRobinDictionary, roundRobinQueue

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

            # print("creating cache file")

            # THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
            # my_file = os.path.join(THIS_FOLDER, 'cache\\' + str(file))
            # temp_file = open(my_file, "wb+")
            # temp_file.write(reply.encode())
            
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
                # print("HTTPS Non blocking Retrieval successfull")c
            except socket.error as err:
                pass
                # print("ending non blocking socket")
                # break

            try:
                reply = s.recv(4096)
                # temp_file.write(reply)
                connection.sendall(reply)
                # print("HTTPS Non blocking Receival successfull")
            except socket.error as err:
                pass
                # print("ending non blocking connection")
                # break


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

    my_file = os.path.join(THIS_FOLDER, 'fifo.txt')

    try:
        fifo_file = open(my_file, 'r')
    except FileNotFoundError:
        fifo_file = open(my_file, 'w+')

    lines = fifo_file.readlines()

    for line in lines:
        if line != '\n':
            line = line.replace('\n', '')
            priorityQueue.append(line)

    fifo_file.close()

    my_file = os.path.join(THIS_FOLDER, 'round_robin.txt')

    try:
        roundRobin_file = open(my_file, 'r')
    except FileNotFoundError:
        roundRobin_file = open(my_file, 'w+')

    lines = roundRobin_file.readlines()

    for line in lines:
        if line != '\n':
            line = line.replace('\n', '')
            roundRobinQueue.append(line)

    roundRobin_file.close()

    my_file = os.path.join(THIS_FOLDER, 'scheduleingMode.txt')

    try:
        schedFile = open(my_file, 'r')
        schedulingMode = schedFile.read()
        print(schedulingMode)
    except FileNotFoundError:
        schedFile = open(my_file, 'w+')
        schedFile.write(schedulingMode)
    schedFile.close()
    

    while 1:
        os.system("cls")
        print("Enter a number to select:\n")
        print("1. Filter content (Add Site/IP and websites to blacklist)")
        print("2. Allow content (Remove Site/IP and websites from blacklist)")
        print("3. Choose cache scheduling method.")
        print("4. Start proxy server.")
        print("5. Exit")
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
            while 1:
                os.system('cls')
                print('Choose a scheduling algorithm. WARNING: All previous cache will be deleted.')
                print("\n1. FIFO")
                print("2. Round Robin")

                inp2 = input('Enter a number to select, press b to go back: ')
                if inp2 == 'b':
                    break
                if inp2 == '1':
                    schedulingMode = 'fifo'
                    priorityQueue = []
                    roundRobinQueue = []
                    roundRobinDictionary = dict()

                    my_file = os.path.join(THIS_FOLDER, 'scheduleingMode.txt')
                    schedFile = open(my_file, 'w')
                    schedFile.write(schedulingMode)
                    schedFile.close()

                    my_file = os.path.join(THIS_FOLDER, 'cache\\*')
                    files = glob.glob(my_file)
                    for f in files:
                        os.remove(f)

                    my_file = os.path.join(THIS_FOLDER, 'fifo.txt')
                    temp = open(my_file, 'w')
                    temp.close()

                    my_file = os.path.join(THIS_FOLDER, 'round_robin.txt')
                    temp = open(my_file, 'w')
                    temp.close()

                    print("Cache scheduling changed to FIFO. All previous cache wiped out.")
                    print("Press Enter to continue.")
                    input()
                    break

                elif inp2 == '2':
                    schedulingMode = 'round_robin'
                    priorityQueue = []
                    roundRobinQueue = []
                    roundRobinDictionary = dict()

                    my_file = os.path.join(THIS_FOLDER, 'scheduleingMode.txt')
                    schedFile = open(my_file, 'w')
                    schedFile.write(schedulingMode)
                    schedFile.close()

                    my_file = os.path.join(THIS_FOLDER, 'cache\\*')
                    files = glob.glob(my_file)
                    for f in files:
                        os.remove(f)

                    my_file = os.path.join(THIS_FOLDER, 'fifo.txt')
                    temp = open(my_file, 'w')
                    temp.close()

                    my_file = os.path.join(THIS_FOLDER, 'round_robin.txt')
                    temp = open(my_file, 'w')
                    temp.close()

                    print("Cache scheduling changed to Round Robin.3 All previous cache wiped out.")
                    print("Press Enter to continue.")
                    input()
                    break
                
                else:
                    print("Invalid input. Please try again.")
                    print("Press Enter to continue.")
                    input()
                    continue

        elif inp == 4:
            start(6543)

        elif inp == 5:
            break

        else:
            print("Invalid input. Press Enter to try again.")
            input()