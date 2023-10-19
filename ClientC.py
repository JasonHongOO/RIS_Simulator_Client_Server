import sys, struct, time, json, signal,random 
import socket
import threading

import datetime
import Const

# ===========================================
# Socker 參數
NAME = "Move_Simulator"

# 全域變數
running = True
Cur_Case_Value = 0
Cur_Angle_Value = 0
Target_Angle_Value = 0
Cur_RSRP_Value = 0
# ===========================================

def signal_handler(sig, frame):
    print("接收到Ctrl+C信號，正在停止服務器...")
    global running
    running = False

    # 執行清理操作，例如關閉套接字和停止線程
    send_thread.join()
    receive_thread.join()

    client_socket.close()
    sys.exit(0)

def receive_messages(client_socket):
    global Cur_Case_Value, Target_Angle_Value
    while running == True:
        try :
            message_length_data = client_socket.recv(4)
            if not message_length_data: break

            message_length = struct.unpack('!I', message_length_data)[0]
            data = client_socket.recv(message_length)
            received_data = json.loads(data.decode('utf-8'))
            print(f"\n來自 {received_data['Sender_Name']} 的消息: {received_data['Msg']}")

            print(received_data)
            if received_data['Sender_Name'] == "xApp":
                print(f"Cur_Case_Value : {received_data['Cur_Case_Value']}")
                Cur_Case_Value = received_data['Cur_Case_Value']
                print(f"Cur_Case_Value : {Cur_Case_Value}")

            elif received_data['Sender_Name'] == "GUI":
                print(f"Target_Angle_Value : {received_data['Target_Angle_Value']}")
                Target_Angle_Value = received_data['Target_Angle_Value']

        except socket.timeout:
            print("等待訊息超時 => 休息一下")
            time.sleep(Const.C_RECEIVER_INTERVAL)

def send_message(client_socket, message):
    message_json = json.dumps(message)
    print(f"SEND message : {message_json}")
    message_length = len(message_json)
    client_socket.send(struct.pack('!I', message_length))  # 發送消息長度
    client_socket.send(message_json.encode('utf-8'))  # 發送消息內容

def send_messages(client_socket):
    while running == True:
        # =============================================
        #                     xApp
        # =============================================
        message = {}
        message["Sender_Name"] = NAME
        message["Receiver_Name"] = []
        message["Receiver_Name"].append("xApp")
        message["Msg"] = "Move Info"
        message['Cur_RSRP_Value'] = Cur_RSRP_Value
        message['Cur_Angle_Value'] = Cur_Angle_Value
        message['Cur_Case_Value'] = Cur_Case_Value
        print(f"SEND message : {message}")
        send_message(client_socket, message)
        
        # =============================================
        #                   GUI
        # =============================================
        message = {}
        message["Sender_Name"] = NAME
        message["Receiver_Name"] = []
        message["Receiver_Name"].append("GUI")
        message["Msg"] = "Move Info"
        message['Cur_Angle_Value'] = Cur_Angle_Value
        message['Target_Angle_Value'] = Target_Angle_Value
        message['Cur_RSRP_Value'] = Cur_RSRP_Value
        send_message(client_socket, message)

        time.sleep(Const.C_SENDER_INTERVAL)

class MoveSimulator:
    def __init__(self):
        self.CaseData, self.CaseDataBehind = ReadJsonData()
        self.increment = Const.STEP_OFFEST_BASE
        self.timer = 0
        self.timer_Max = 1
        self.State = 0

    def Start(self):
        self.Updata()

    def Updata(self):
        global running, Cur_Case_Value, Cur_Angle_Value, Target_Angle_Value, Cur_RSRP_Value

        while running:
            if Cur_Angle_Value != Target_Angle_Value:
                if Cur_Angle_Value < Target_Angle_Value:
                    Cur_Angle_Value += self.increment + (random.randint(Const.STEP_OFFEST_MIN, Const.STEP_OFFEST_MAX) if Const.STEP_RANDOM_ACTIVATE == True else 0)
                else:
                    Cur_Angle_Value -= self.increment + (random.randint(Const.STEP_OFFEST_MIN, Const.STEP_OFFEST_MAX) if Const.STEP_RANDOM_ACTIVATE == True else 0)

                if Cur_Angle_Value > Const.ANGLE_MAX: Cur_Angle_Value = Const.ANGLE_MAX
                elif Cur_Angle_Value < Const.ANGLE_MIN: Cur_Angle_Value = Const.ANGLE_MIN
                    

            # 隨機移動
            # if Cur_Angle_Value == 0 and self.State == 0: 
            #     if self.timer < 8 : self.timer += 1
            #     else:
            #         self.State = 1
            #         self.timer = 0
            #         positive_random_int = random.randint(0, 60)
            #         if positive_random_int != 0: random_integer = positive_random_int * random.choice([1, -1])
            #         else : random_integer = 0
            #         Target_Angle_Value = random_integer

            # elif self.State == 1: 
            #     if self.timer < self.timer_Max : self.timer += 1
            #     else:
            #         self.State = 2
            #         self.timer = 0
                
            # elif self.State == 2: 
            #     self.State = 1
            #     positive_random_int = random.randint(0, 60)
            #     if positive_random_int != 0: random_integer = positive_random_int * random.choice([1, -1])
            #     else : random_integer = 0
            #     Target_Angle_Value = random_integer

                    
            # 0 -> 60 -> 0
            if Cur_Angle_Value == 0 and self.State == 0: 
                if self.timer < self.timer_Max : 
                    self.timer += 1
                else:
                    self.State = 1
                    Target_Angle_Value = 60
                    self.timer = 0
            elif Cur_Angle_Value == 60 and self.State == 1: 
                if self.timer < self.timer_Max : self.timer += 1
                else:
                    self.State = 2
                    Target_Angle_Value = 0
                    self.timer = 0
            elif Cur_Angle_Value == 0 and self.State == 2: 
                if self.timer < self.timer_Max : self.timer += 1
                else:
                    self.State = 3
                    self.timer = 0

            # print(f"self.timer : {self.timer}")


            Cur_RSRP_Value = self.CaseDataBehind['Case'][str(Cur_Case_Value)]['Angle'][str(Cur_Angle_Value)]
            Cur_RSRP_Value = Cur_RSRP_Value + (random.randint(Const.RSRP_OFFEST_MIN, Const.RSRP_OFFEST_MAX) if Const.RSRP_FLUCTUATING_ACTIVATE == True else 0) * random.choice([1, -1])

            time.sleep(random.uniform(1, 2)) 


def ReadJsonData():
    Data_Fixed_Json_Path = Const.DATA_FILE
    with open(Data_Fixed_Json_Path, 'r') as f:
        Data_Fixed_Json = json.load(f)

    Data_Fixed_Behind_Json_Path = Const.DATA_BEHIND_FILE
    with open(Data_Fixed_Behind_Json_Path, 'r') as f:
        Data_Fixed_Behind_Json = json.load(f)

    return Data_Fixed_Json, Data_Fixed_Behind_Json

if __name__ == "__main__":
    host = '127.0.0.1'
    port = 12345

    signal.signal(signal.SIGINT, signal_handler)
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))
    client_socket.settimeout(5)

    client_name = NAME
    message_length = len(client_name)
    client_socket.send(struct.pack('!I', message_length))  # 發送消息長度
    client_socket.send(client_name.encode('utf-8'))  # 發送用戶名給服務器

    receive_thread = threading.Thread(target=receive_messages, args=(client_socket,))
    send_thread = threading.Thread(target=send_messages, args=(client_socket,))

    receive_thread.start()
    send_thread.start()


    Mover = MoveSimulator()
    Mover.Start()
