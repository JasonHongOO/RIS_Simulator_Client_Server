import numpy as np

def mea2state(mea):             # 輸入是一個 column，在最下面加 0
    return np.row_stack((mea, np.zeros((1, 1))))


def state2mea(state):
    return state[0:1]       # 就是 state.X_prior[0]


if __name__ == "__main__":
    print(mea2state(np.array([[1,2,3,4]]).T))
