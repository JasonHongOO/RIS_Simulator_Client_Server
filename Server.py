import sys, struct, time, json, signal,random
import socket
import threading
 
import Const

running = True
client_sockets = {}
Thread_Record = []

def signal_handler(sig, frame):
    print("接收到Ctrl+C信號，正在停止服務器...")
    global running
    running = False

    # 執行清理操作，例如關閉套接字和停止線程
    for Thread in Thread_Record:
        Thread.join()
    server_socket.close()
    sys.exit(0)

def send_message(client_socket, message):
    message_json = json.dumps(message)
    message_length = len(message_json)
    client_socket.send(struct.pack('!I', message_length))  # 發送消息長度
    client_socket.send(message_json.encode('utf-8'))  # 發送消息內容

def broadcast(sender_id, message):
    for client_id, client_socket in client_sockets.items():
        if client_id != sender_id:
            try:
                client_socket.send(message)
            except:
                del client_sockets[client_id]
                client_socket.close()

def handle_client(client_socket, client_name):
    client_address = client_socket.getpeername()
    print(f"\n與客戶端 {client_name} ({client_address}) 連接成功")
    client_sockets[client_name] = client_socket

    try:
        while running == True:
            message_length_data = client_socket.recv(4)
            if not message_length_data: break

            message_length = struct.unpack('!I', message_length_data)[0]
            data = client_socket.recv(message_length)
            if not data: break

            # 處理來自客戶端的消息
            received_data = json.loads(data.decode('utf-8'))
            print(f"來自 {client_name} 給 {received_data['Receiver_Name']} 的消息: {received_data['Msg']}")
            print(received_data)

            # 轉寄
            for Receiver_Name in received_data['Receiver_Name'] :
                if Receiver_Name in client_sockets :
                    message = received_data
                    Target_client_socket = client_sockets[Receiver_Name]
                    send_message(Target_client_socket, message)
                else :
                    print(f"{Receiver_Name} 未與伺服器連線")

            time.sleep(Const.SERVER_INTERVAL)

    except Exception as e:
        print(f"與客戶端 {client_name} 發生錯誤: {str(e)}")

    client_socket.close()
    print(f"與客戶端 {client_name} 斷開連接")


if __name__ == "__main__":
    host = '0.0.0.0'
    port = 12345
    signal.signal(signal.SIGINT, signal_handler)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.settimeout(5)
    server_socket.listen(10)        # queue

    while True:
        try:
            print("等待客戶端連接...")
            client_socket, client_address = server_socket.accept()

            message_length_data = client_socket.recv(4)
            message_length = struct.unpack('!I', message_length_data)[0]
            client_name = client_socket.recv(message_length).decode('utf-8')  # 接收客戶端發送的用戶名
            client_handler = threading.Thread(target=handle_client, args=(client_socket, client_name))
            Thread_Record.append(client_handler)
            client_handler.start()
        except socket.timeout:
            print("等待 Client 連線時間超過 => 休息一下")
            time.sleep(1)
            pass
