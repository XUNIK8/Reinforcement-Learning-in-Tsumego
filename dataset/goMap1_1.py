import numpy as np

def limitSearchSpace(startRow=0,startColumn=0,endRow=12,endColumn=12):
    channel = np.zeros((13,13))
    for i in range(startRow,endRow+1):
        for j in range(startColumn,endColumn+1):
            channel[i][j] = 1

    return 1 - channel

# 黑子初始位置
channel1 = [
        [0, 0, 0, 1],
        [0, 0, 0, 1],
        [0, 0, 0, 1],
        [0, 0, 1, 1],
        [1, 1, 1, 0],
        [0, 0, 0, 0]

    ]
# 白子初始位置
channel2 = [
        [0, 0, 1, 0],
        [0, 0, 1, 0],
        [0, 0, 1, 0],
        [1, 1, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0]

    ]
# 无意义搜索空间（有意义0，无意义1）
channel3 = np.zeros((6,4))
# 无效位置(有效0，无效1)
channel4 = channel3 + channel2 + channel1
# 下一步落子方：黑0，白1
channel5 = np.ones((6,4))
# 上一步是否为Pass（否0，是1）
channel6 = np.zeros((6,4))
# 上一步后是否结束游戏（否0，是1）
channel7 = np.zeros((6,4))

originalgoMap = np.array([channel1,channel2,channel3,channel4,channel5,channel6,channel7])
survivePlayer = 1 # 黑0 白1
