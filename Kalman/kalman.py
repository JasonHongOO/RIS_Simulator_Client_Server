import random
import numpy as np
from . import utils

GENERATE_SET = 1 
TERMINATE_SET = 7


class Kalman:
    def __init__(self, A, B, H, Q, R, X, P):
        # 固定參數
        self.A = A  # 狀態轉移矩陣
        self.B = B  # 控制矩陣
        self.H = H  # 觀測矩陣
        self.Q = Q  # "過程" 噪聲
        self.R = R  # "觀測' 噪聲
        # 蝶帶
        self.X_posterior = X  
        self.P_posterior = P 
        self.X_prior = None 
        self.P_prior = None  
        self.K = None  # kalman gain
        self.Z = None  # 觀測資料, 定義為 [中心x,中心y,寬w,高h] 
        # 起始和終止策略
        self.terminate_count = TERMINATE_SET
        # (暫存)移動軌跡
        self.track = []
        self.track_color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        self.__record_track()

    def predict(self):
        self.X_prior = np.dot(self.A, self.X_posterior)                                                             #少了 Bu !! (沒有控制輸入矩陣)
        self.P_prior = np.dot(np.dot(self.A, self.P_posterior), self.A.T) + self.Q                                  # self.Q



        return self.X_prior, self.P_prior       

    def update(self, mea=None):
        status = True
        if mea is not None:                 # 有資料就會來這邊
            self.Z = mea
            self.K = np.dot(np.dot(self.P_prior, self.H.T),     
                            np.linalg.inv(np.dot(np.dot(self.H, self.P_prior), self.H.T) + self.R))                 # self.R
            self.X_posterior = self.X_prior + np.dot(self.K, self.Z - np.dot(self.H, self.X_prior))  
            self.P_posterior = np.dot(np.eye(2) - np.dot(self.K, self.H), self.P_prior)                             # 矩陣記得要改成 kalman filter 資料的大小
            status = True
        else:
            self.X_posterior = self.X_prior
            self.P_posterior = self.P_prior

        if status:
            self.__record_track()

        return status, self.X_posterior, self.P_posterior

    def __record_track(self):
        self.track.append([int(self.X_posterior[0])])           #紀錄 RSRP





if __name__ == '__main__':
    
    A = np.array([[1, 1],
              [0, 1]])

    B = None

    Q = np.eye(A.shape[0]) * 0.1        #對角線為 0.1

    H = np.array([[1, 0]])

    R = np.eye(H.shape[0]) * 1

    P = np.eye(A.shape[0])



    print("=================================")
    print("             Predict")
    print("=================================")

    meas = [10]
    X = utils.mea2state(meas)
    print(X)

    k1 = Kalman(A, B, H, Q, R, X, P)
    X_prior, P_prior = k1.predict()
    print("=================================")
    print(f"X_prior : \n{X_prior}")
    print(f"P_prior : \n{P_prior}")

    print("=================================")
    print("             Correct")
    print("=================================")

    mea = [20]
    # mea = utils.mea2state(mea)
    status, X_posterior, P_posterior = k1.update(mea)
    print("=================================")
    print(f"status : {status}")
    print(f"X_posterior : \n{X_posterior}")
    print(f"P_posterior : \n{P_posterior}")


    print("=================================")
    print("             Predict")
    print("=================================")

    X_prior, P_prior = k1.predict()
    print("=================================")
    print(f"X_prior : \n{X_prior}")
    print(f"P_prior : \n{P_prior}")

    print("=================================")
    print("             Correct")
    print("=================================")

    mea = [20]
    # mea = utils.mea2state(mea)
    status, X_posterior, P_posterior = k1.update(mea)
    print("=================================")
    print(f"status : {status}")
    print(f"X_posterior : \n{X_posterior}")
    print(f"P_posterior : \n{P_posterior}")




    