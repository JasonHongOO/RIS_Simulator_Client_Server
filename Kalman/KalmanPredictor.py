import cv2
import numpy as np
from . import const
from . import utils
from .kalman import Kalman



class KalmanPredictor:
    def __init__(self, MainComponent):
        self.ParentComponent = MainComponent
        self.KalmanExist = False

        # --------------------------------Kalman參數---------------------------------------
        # 狀態轉移矩陣，上一時刻的狀態轉移到當前時刻
        self.A = np.array([[1, 1],
                           [0, 1]])

        # 控制輸入矩陣B
        self.B = None

        # 過程噪聲協方差矩陣
        self.Q = np.eye(self.A.shape[0]) * 0.1        #對角線為 0.1
        # 狀態觀測矩陣
        self.H = np.array([[1, 0]])

        # 觀測噪聲協方差矩陣
        self.R = np.eye(self.H.shape[0]) * 1
        # 狀態估計協方差矩陣
        self.P = np.eye(self.A.shape[0])
        # -------------------------------------------------------------------------------
        
        self.state_data = None  # 單幀目標狀態信息，存kalman                     # 就是一個 kalman 物件
        self.state_data_list = []

        self.PredictResult = "None"
        self.PrePredictResult = "None"


    def KalmanFilter(self, meas_data=None, Name="None"):
        # 紀錄上一回的資料
        if self.PredictResult != "None":
            self.PrePredictResult = self.PredictResult

        self.CurMeasData = meas_data

        # ========================================================================================
        #                                   Kalman Filter(multi-objects)
        # ========================================================================================
        
        if self.KalmanExist == True and self.state_data != None:
            # 預測
            self.state_data.predict()
            # 更新
            self.state_data.update(self.CurMeasData)      

        # 觀測值沒匹配到則認定為是新生目標，創建新的 Kalman Filter 給該新生目標使用
        elif self.KalmanExist == False:
            self.state_data_list.append(Kalman(self.A, self.B, self.H, self.Q, self.R, utils.mea2state(self.CurMeasData), self.P))
            self.state_data = self.state_data_list[0]
            

        if(self.KalmanExist == False): 
            self.KalmanExist = True
        else: 
            self.PredictResult = round(utils.state2mea(self.state_data.X_posterior)[0][0], 6)
            self.PrintResult()
    
        
    def PrintResult(self):
        # ========================================================================================
        #                                   畫圖
        # ========================================================================================
        
        # 顯示(觀測資料)
        # print("Cur Input Data : ", self.CurMeasData)           # 就是輸入的資料

        # 顯示(預測資料)
        # self.PredictResult = utils.state2mea(self.state_data.X_posterior)[0][0]
        # self.PredictResult = round(self.PredictResult, 6)
        # print("Cur Predict Data : ", self.PredictResult)
        
        # 將匹配關系畫出來(更新幅度、方向)
        # for item in match_list:
        #     cv2.line(frame, tuple(item[0][:2]), tuple(item[1][:2]), const.COLOR_MATCH, 3)


        # 繪制軌跡              (從 0 時刻 ~ 現在的軌跡畫出來) 
        tracks_list = self.state_data.track                  
        for idx in range(len(tracks_list) - 1):
            last_frame = tracks_list[idx]
            cur_frame = tracks_list[idx + 1]
            # cv2.line(frame, last_frame, cur_frame, kalman.track_color, 2)



        # print("=============================================================")




if __name__ == '__main__':
    class KalmanTest:
        def __init__(self):
            self.AngleKalmanExist = False

    temp = KalmanTest()
    Object = KalmanPredictor(temp)
    Object.KalmanFilter(11)
    Object.KalmanFilter(12)
    Object.KalmanFilter(13)
    Object.KalmanFilter(14)
    Object.KalmanFilter(15)
    Object.KalmanFilter(16)
