import sys, struct, time, json, signal,random
import socket
import threading

import numpy as np 
import datetime
import Const
from Kalman.KalmanPredictor import KalmanPredictor
from TextColor import *


# ===========================================
# Socker 參數
NAME = "xApp"

# 全域變數
running = True
Cur_Case_Value = 0
Cur_Angle_Value = 0
Target_Angle_Value = 0
Cur_RSRP_Value = 0

# xApp
Angle_Kalman_PredictResult = 0
Angle_Kalman_PrePredictResult = 0
RSRP_Kalman_PredictResult = 0
RSRP_Kalman_PrePredictResult = 0

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

def receive_messages(client_socket, xApp_Simulator):
    global Cur_RSRP_Value, Cur_Angle_Value
    while running == True:
        try :
            message_length_data = client_socket.recv(4)
            if not message_length_data: break

            message_length = struct.unpack('!I', message_length_data)[0]
            data = client_socket.recv(message_length)
            received_data = json.loads(data.decode('utf-8'))
            print(f"\n來自 {received_data['Sender_Name']} 的消息: {received_data['Msg']}")

            print(received_data)
            if received_data['Sender_Name'] == "Move_Simulator":
                print(f"Cur_RSRP_Value : {received_data['Cur_RSRP_Value']}")
                Cur_RSRP_Value = received_data['Cur_RSRP_Value']
                
                print(f"Cur_Angle_Value : {received_data['Cur_Angle_Value']}")
                Cur_Angle_Value = received_data['Cur_Angle_Value']

                print(f"Cur_Case_Value : {received_data['Cur_Case_Value']}")

                # Update xApp Info
                xApp_Simulator.Updata_State()

            if received_data['Sender_Name'] == "GUI":
                print(f"ERROR : {False}")
                
            
        except socket.timeout:
            print("等待訊息超時 => 休息一下")
            time.sleep(Const.B_RECEIVER_INTERVAL)

def send_message(client_socket, message):
    message_json = json.dumps(message)
    message_length = len(message_json)
    client_socket.send(struct.pack('!I', message_length))  # 發送消息長度
    client_socket.send(message_json.encode('utf-8'))  # 發送消息內容

def send_messages(client_socket):
    while running == True:
        # =============================================
        #               Move_Simulator
        # =============================================
        message = {}
        message["Sender_Name"] = NAME
        message["Receiver_Name"] = []
        message["Receiver_Name"].append("Move_Simulator")
        message["Msg"] = "xApp Info"
        message['Cur_Case_Value'] = Cur_Case_Value
        send_message(client_socket, message)

        # =============================================
        #                   GUI
        # =============================================
        message = {}
        message["Sender_Name"] = NAME
        message["Receiver_Name"] = []
        message["Receiver_Name"].append("GUI")
        message["Msg"] = "Move Info"
        message['Cur_Case_Value'] = Cur_Case_Value
        message['Angle_Kalman_PredictResult'] = Angle_Kalman_PredictResult
        message['Angle_Kalman_PrePredictResult'] = Angle_Kalman_PrePredictResult
        message['RSRP_Kalman_PredictResult'] = RSRP_Kalman_PredictResult
        message['RSRP_Kalman_PrePredictResult'] = RSRP_Kalman_PrePredictResult
        send_message(client_socket, message)

        time.sleep(Const.B_SENDER_INTERVAL)


class HandOverSimulator:
    def __init__(self):
        self.CaseData, self.CaseDataBehind = ReadJsonData()              # 輻射場型資料
        # self.Target_Angle_Value = 0
        self.Cur_Angle_Value = 0
        self.Cur_RSRP_Value = 0
        self.Cur_Case_Value = 0
        self.Old_Case_Value = 0

        self.AngleKalman = KalmanPredictor(self)
        self.AngleKalman.KalmanFilter(0, "Angle")
        self.RSRPKalman = KalmanPredictor(self)
        self.AngleKalmanState = True                     # True 有資料的更新、 False 無資料的更新    
        self.RSRPKalmanState = True                     # True 有資料的更新、 False 無資料的更新    

        # 過程參數
        self.current_time = ""
        self.cur_err_time = ""
        self.pre_err_time = ""
        
        self.HandoverCheck = False
        self.HandoverThreshold = Const.HANDOVER_THRESHOLD      
        self.SortPotentialList = []
        self.SortPotentialListByPredict = []
        self.QueueCnt = 1                               # 0 是最開始切換的，1 開始是切換補救

        self.Check_RSRP_State = 0
        self.Check_RSRP_Sum = 0
        self.Check_RSRP_Avg = 0
        
        # 暫時使用的變數
        self.Receiver_Timer = 0

    def Updata_State(self):
        def Angle_Predictor(Cur_Case_Value=None):
            global Angle_Kalman_PredictResult, Angle_Kalman_PrePredictResult
            # ================================================================================================ #
            #                                         RIS Case 預測  
            # ================================================================================================ #
            self.AngleKalman.KalmanFilter(Cur_Case_Value, "Angle")
            Angle_Kalman_PredictResult = self.AngleKalman.PredictResult
            Angle_Kalman_PrePredictResult = self.AngleKalman.PrePredictResult

        def RSRP_Predictor(Cur_RSRP_Value=None):
            global RSRP_Kalman_PredictResult, RSRP_Kalman_PrePredictResult
            # ================================================================================================ #
            #                                       RSRP 預測   
            # ================================================================================================ #
            self.RSRPKalman.KalmanFilter(Cur_RSRP_Value, "RSRP")
            RSRP_Kalman_PredictResult = self.RSRPKalman.PredictResult
            RSRP_Kalman_PrePredictResult = self.RSRPKalman.PrePredictResult
        
        global running, Cur_RSRP_Value, Cur_Case_Value, Cur_Angle_Value
        self.Cur_Angle_Value = Cur_Angle_Value
        self.Cur_RSRP_Value = Cur_RSRP_Value
        # self.Cur_Case_Value = Cur_Case_Value

        self.current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        max_key = float(max(self.CaseData['Case'][str(self.Cur_Case_Value)]['RSRP'], key=float))
        min_key = float(min(self.CaseData['Case'][str(self.Cur_Case_Value)]['RSRP'], key=float)) 
        if (self.Cur_RSRP_Value > max_key): self.Cur_RSRP_Value = max_key
        elif (self.Cur_RSRP_Value < min_key): self.Cur_RSRP_Value = min_key

        # ================================================================================================ #
        #                                     確認 Handover 結果是否正確  
        # ================================================================================================ #
        if self.HandoverCheck == True:      
            # 切換正確 (如果是正確的，則理應當 RSRP 要變好)
            if self.Cur_RSRP_Value >= self.HandoverThreshold:            
                self.RSRPKalmanState = True
                self.HandoverCheck = False

                self.RSRPKalman = KalmanPredictor(self)          
                RSRP_Predictor(self.Cur_RSRP_Value)
                RSRP_Predictor(None)

                print("(Correct)")
                print(f"Ori : {self.AngleKalman.PredictResult}")
                Angle_Predictor(self.Cur_Case_Value)
                print(f"Update : {self.AngleKalman.PredictResult}")
                Angle_Predictor(None)
                print(f"First : {self.AngleKalman.PredictResult}")
                Angle_Predictor(None)
                print(f"Second : {self.AngleKalman.PredictResult}")

                if(self.QueueCnt <= Const.TERMINATE_SET):
                    print(f"小於限制次數 : {self.QueueCnt}")
                    for idx, i in enumerate(range(1,self.QueueCnt+1,2)):
                        Angle_Predictor(None)
                        print(f"({idx}) : {self.AngleKalman.PredictResult}")

                self.QueueCnt = 1
                print(f"Handover 正確!!!! (目前 RIS 角度 : {self.Cur_Case_Value}) (收到 RSRP : {self.Cur_RSRP_Value}) (真正位置為 : {self.Cur_Angle_Value})")
                print("=====================================================================")
                return

            # 切換錯誤 (需要嘗試補救)       
            else:
                if self.Receiver_Timer < Const.RECEIVER_TIMER_NUM:
                    self.Receiver_Timer += 1
                    print(f"RSRP 低於 Threshold 但還有等待機會 : {self.Receiver_Timer}")
                    return
                else :
                    self.Receiver_Timer = 0
                    print(f"Handover 錯了!!!! (目前 RIS 角度 : {self.Cur_Case_Value}) (收到 RSRP : {self.Cur_RSRP_Value}) (真正位置為 : {self.Cur_Angle_Value})")
                    if self.QueueCnt > Const.TERMINATE_SET or self.QueueCnt >= len((self.SortPotentialList if Const.PREDICT_ANGLE_ACTIVATE == False else self.SortPotentialListByPredict)):
                        self.RSRPKalman = KalmanPredictor(self)         # 不論切正確與否，重新初始化
                        RSRP_Predictor(self.Cur_RSRP_Value)
                        RSRP_Predictor(None)

                        if(Const.RECOVERY_ACTIVATE == False):                               # 回頭補救機制
                            print("(Error)")
                            print(f"Ori : {self.AngleKalman.PredictResult}")
                            Angle_Predictor(self.Old_Case_Value - (self.AngleKalman.PredictResult - self.Old_Case_Value))
                            print(f"Update : {self.AngleKalman.PredictResult}")
                            Angle_Predictor(None)
                            print(f"First : {self.AngleKalman.PredictResult}")
                            Angle_Predictor(None)
                            print(f"Second : {self.AngleKalman.PredictResult}")
                            Angle_Predictor(None)
                            print(f"Third : {self.AngleKalman.PredictResult}")
                        else:                                                               # 復原機制
                            self.Cur_Case_Value = self.Old_Case_Value
                            Cur_Case_Value = self.Cur_Case_Value # Output
                            self.AngleKalman = KalmanPredictor(self)   
                            Angle_Predictor(self.Cur_Case_Value)
                            print(f"回復於原始位置 : CASE({self.Old_Case_Value})")
                        
                        self.QueueCnt = 1
                        self.HandoverCheck = False
                        self.RSRPKalmanState = True
                        print("跟丟目標")
                        print("=====================================================================")
                        return
                    else:
                        self.Cur_Case_Value = (self.SortPotentialList[self.QueueCnt] if Const.PREDICT_ANGLE_ACTIVATE == False else self.SortPotentialListByPredict[self.QueueCnt])
                        Cur_Case_Value = self.Cur_Case_Value # Output
                        self.QueueCnt += 1          #嘗試補救
                        print(f"(嘗試補救) 切 : {self.Cur_Case_Value}")
                        print("=====================================================================")
                        time.sleep(Const.INTERVAL_TIME)
                        return


        # ============================================================================================================ #
        #                                 更新 kalman filter 、 判斷是否需要 handover  
        # ============================================================================================================ #
        if self.RSRPKalmanState == True:
            RSRP_Predictor(self.Cur_RSRP_Value)
            RSRP_Predictor(None)

            if self.Check_RSRP_State == 0:
                if self.Cur_RSRP_Value < self.HandoverThreshold:        # 訊號夠差，發現可能要切換 Case
                    self.Check_RSRP_State += 1
                    self.Check_RSRP_Sum = self.Cur_RSRP_Value

            else:                                                       # 收集近幾筆資料，確認是否真的是要切換 Case
                if self.Check_RSRP_State < Const.CHECK_RSRP_AVG_NUM:
                    self.Check_RSRP_State += 1
                    self.Check_RSRP_Sum += self.Cur_RSRP_Value
                else:
                    self.Check_RSRP_State = 0
                    self.Check_RSRP_Avg = round(self.Check_RSRP_Sum/Const.CHECK_RSRP_AVG_NUM, 1)
                    print(f"RSRP_Avg({Const.CHECK_RSRP_AVG_NUM}s) : {self.Check_RSRP_Avg} / Threshold : {self.HandoverThreshold}")
                    print(f"=====================================================================")

                    if self.Check_RSRP_Avg < self.HandoverThreshold: 
                        self.RSRPKalmanState = False                        # RSRP 的預測開始不放入觀測值，因為 Case 已切換，但我仍需原本 Case 的資訊

                        # 第一次切換
                        self.Old_Case_Value = self.Cur_Case_Value
                        if self.Cur_Case_Value != 0:
                            self.Cur_Case_Value = -self.Cur_Case_Value      # 切成反方向
                            Cur_Case_Value = self.Cur_Case_Value # Output
                        else:
                            self.Cur_Case_Value = 30 
                            Cur_Case_Value = self.Cur_Case_Value # Output

                        if(self.cur_err_time != "") : self.pre_err_time = self.cur_err_time
                        self.cur_err_time = int(datetime.datetime.now().strftime("%S"))

            return
        else:
            if self.Receiver_Timer < Const.RECEIVER_TIMER_NUM:
                self.Receiver_Timer += 1
            else :
                self.Receiver_Timer = 0
                RSRP_Predictor(None)
                Angle_Predictor(None)

                # 根據 RSRP 預測值，找出有可能的正確 RIS 角度為何      
                First_Chg_Case_PotentialList = []
                First_Chg_Case_PotentialList = set(First_Chg_Case_PotentialList) 
                for i in np.arange(Const.CASE_CHANGE_SIMPLED_DATA_RANGE_MIN, Const.CASE_CHANGE_SIMPLED_DATA_RANGE_MAX+Const.CASE_CHANGE_SIMPLED_DATA_RANGE_STEP, Const.CASE_CHANGE_SIMPLED_DATA_RANGE_STEP):
                    RSRP_var = self.Cur_RSRP_Value + i
                    if RSRP_var > max_key : RSRP_var = max_key
                    elif RSRP_var < min_key : RSRP_var = min_key
                    First_Chg_Case_PotentialList |= set(self.CaseData['Case'][str(self.Cur_Case_Value)]['RSRP'][str(RSRP_var)])
                First_Chg_Case_PotentialList = list(First_Chg_Case_PotentialList) 
                print(f"First_Chg_Case_PotentialList_Range : {self.Cur_RSRP_Value+Const.CASE_CHANGE_SIMPLED_DATA_RANGE_MIN}~{self.Cur_RSRP_Value+Const.CASE_CHANGE_SIMPLED_DATA_RANGE_MAX+Const.CASE_CHANGE_SIMPLED_DATA_RANGE_STEP}")

                Ori_PotentialList = []           
                Ori_PotentialList = set(Ori_PotentialList) 
                for i in np.arange(Const.ORI_SIMPLED_DATA_RANGE_MIN, Const.ORI_SIMPLED_DATA_RANGE_MAX+Const.ORI_SIMPLED_DATA_RANGE_STEP, Const.ORI_SIMPLED_DATA_RANGE_STEP):        # Error Range                           # 手動!!!!!!
                    RSRP_var = round(self.RSRPKalman.PredictResult*2)/2 +i
                    if RSRP_var > max_key : RSRP_var = max_key
                    elif RSRP_var < min_key : RSRP_var = min_key
                    Ori_PotentialList |= set(self.CaseData['Case'][str(self.Old_Case_Value)]['RSRP'][str(RSRP_var)])
                Ori_PotentialList = list(Ori_PotentialList) 

                # 相同元素處理
                Common_ElementList = list(set(Ori_PotentialList) & set(First_Chg_Case_PotentialList))
                self.SortPotentialList = sorted(Common_ElementList, key=lambda x: abs(x - self.Old_Case_Value))  
                self.SortPotentialListByPredict = sorted(Common_ElementList, key=lambda x: abs(x - self.AngleKalman.PredictResult))  
                for index in range(len(self.SortPotentialList)):       # range 本來就會少 1
                    if index < len(self.SortPotentialList)-1:
                        if (abs(self.SortPotentialList[index]) == abs(self.SortPotentialList[index+1])) and self.SortPotentialList[index] > 0:
                            self.SortPotentialList[index], self.SortPotentialList[index+1] = self.SortPotentialList[index+1], self.SortPotentialList[index]

                        if (abs(self.SortPotentialListByPredict[index]) == abs(self.SortPotentialListByPredict[index+1])) and self.SortPotentialListByPredict[index] > 0:
                            self.SortPotentialListByPredict[index], self.SortPotentialListByPredict[index+1] = self.SortPotentialListByPredict[index+1], self.SortPotentialListByPredict[index]

                # Log
                print(f"Current Time : {self.current_time}")
                print(f"{bcolors.HEADER}Cur UE Angle : {bcolors.ENDC}{self.Cur_Angle_Value}")
                print(f"{bcolors.HEADER}Kalman_Angle_Value : {bcolors.ENDC}{self.AngleKalman.PredictResult}")
                print(f"{bcolors.OKCYAN}Cur_Case_Value : {bcolors.ENDC}{self.Cur_Case_Value}")
                print(f"{bcolors.OKCYAN}Cur_RSRP_Value : {bcolors.ENDC}{self.Cur_RSRP_Value}")
                print(f"{bcolors.OKCYAN}First_Chg_Case_PotentialList : {bcolors.ENDC}{First_Chg_Case_PotentialList}")
                print(f"{bcolors.OKBLUE}Old_Case_Value : {bcolors.ENDC}{self.Old_Case_Value}")
                print(f"{bcolors.OKBLUE}Kalman_RSRP_Value : {bcolors.ENDC}{self.RSRPKalman.PredictResult}")
                print(f"{bcolors.OKBLUE}Ori_PotentialList : {bcolors.ENDC}{Ori_PotentialList}")
                print(f"{bcolors.WARNING}Common_ElementList : {bcolors.ENDC}{Common_ElementList}")
                print(f"{bcolors.WARNING}Choose_Queue : {bcolors.ENDC}{self.SortPotentialList}")
                print(f"{bcolors.WARNING}Choose_Queue_ByPredict : {bcolors.ENDC}{self.SortPotentialListByPredict}")
                print(f"=====================================================================")

                self.HandoverCheck = True
                if( len(self.SortPotentialList if Const.PREDICT_ANGLE_ACTIVATE == False else self.SortPotentialListByPredict) != 0):
                    self.Cur_Case_Value = (self.SortPotentialList[0] if Const.PREDICT_ANGLE_ACTIVATE == False else self.SortPotentialListByPredict[0])      # 切換 Case
                    Cur_Case_Value = self.Cur_Case_Value # Output

            return
        
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
    xApp_Simulator = HandOverSimulator()

    signal.signal(signal.SIGINT, signal_handler)
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))
    client_socket.settimeout(5)

    client_name = NAME
    message_length = len(client_name)
    client_socket.send(struct.pack('!I', message_length))  # 發送消息長度
    client_socket.send(client_name.encode('utf-8'))  # 發送用戶名給服務器

    receive_thread = threading.Thread(target=receive_messages, args=(client_socket,xApp_Simulator,))
    send_thread = threading.Thread(target=send_messages, args=(client_socket,))

    receive_thread.start()
    send_thread.start()

    while running:
        pass

