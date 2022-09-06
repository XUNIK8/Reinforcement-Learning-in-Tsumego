import numpy as np
from scipy import ndimage

from GymGo import state_utils, govars

"""
The state of the game is a numpy array
* Are values are either 0 or 1

* Shape [NUM_CHNLS, SIZE, SIZE]

0 - Black pieces
CHANNEL[0]: 黑棋棋子分布。有黑棋棋子位置为1，否则为0；
1 - White pieces
CHANNEL[1]: 白棋棋子分布。有白棋棋子位置为1，否则为0；
2 - Turn (0 - black, 1 - white)
CHANNEL[2]: 下一步落子方，一个全0或全1的矩阵。0：黑方，1：白方；
3 - Invalid moves (including ko-protection)
CHANNEL[3]: 下一步的落子无效位置。无效位置为1，其余为0；
4 - Previous move was a pass
CHANNEL[4]: 上一步是否为PASS，一个全0或全1的矩阵。0：不是PASS，1：是PASS；
5 - Game over
CHANNEL[5]: 上一步落子后，游戏是否结束，一个全0或全1的矩阵。0：未结束，1：已结束。
"""

def next_state(state, uselessPosition,action1d, canonical=False):
    # Deep copy the state to modify
    state = np.copy(state)

    # Initialize basic variables
    board_shape = state.shape[1:]  # state.shape为(通道数, 棋盘高度, 棋盘宽度)
    pass_idx = np.prod(board_shape)  # np.prod()将参数内所有元素连乘，pass_idx："pass"对应的id
    passed = action1d == pass_idx  # 如果action id等于pass_idx，则passed为True
    action2d = action1d // board_shape[0], action1d % board_shape[1]  # 将action1d转换成action2d

    player = turn(state)  # 获取下一步落子方
    previously_passed = prev_player_passed(state)  # 获取上一步是否为pass
    ko_protect = None

    if passed:
        # We passed
        # 如果下一步为pass，则将next_state中PASS_CHNL矩阵置为全1矩阵
        state[govars.PASS_CHNL] = 1
        if previously_passed:
            # Game ended
            # 如果上一步也为pass，则游戏结束【双方连续各pass，则游戏结束】
            # 将next_state中DONE_CHNL矩阵置为全1矩阵
            state[govars.DONE_CHNL] = 1
    else:
        # Move was not pass
        state[govars.PASS_CHNL] = 0

        # Assert move is valid    检查落子是否有效【state中INVD_CHNL对应位置为0】
        assert state[govars.INVD_CHNL, action2d[0], action2d[1]] == 0, ("Invalid move", action2d)

        # Add piece
        state[player, action2d[0], action2d[1]] = 1

        # Get adjacent location and check whether the piece will be surrounded by opponent's piece
        # 获取下一步落子位置的相邻位置（仅在棋盘内）、下一步落子位置是否被下一步落子方对手的棋子包围
        adj_locs, surrounded = state_utils.adj_data(state, action2d, player)

        # Update pieces
        # 更新棋盘黑白棋子分布矩阵，并返回各组被杀死的棋子列表
        killed_groups = state_utils.update_pieces(state, adj_locs, player)

        # If only killed one group, and that one group was one piece, and piece set is surrounded,
        # activate ko protection
        if len(killed_groups) == 1 and surrounded:
            killed_group = killed_groups[0]
            if len(killed_group) == 1:
                ko_protect = killed_group[0]

    # Update invalid moves

    state[govars.INVD_CHNL] = state_utils.compute_invalid_moves(state, uselessPosition,player, ko_protect)

    # Switch turn
    # 设置下一步落子方
    state_utils.set_turn(state)

    # 该标记是选择是否始终以黑棋视角看待当前游戏局面
    if canonical:
        # Set canonical form
        # 该函数将黑白棋子分布对换，并更改下一手落子方为黑棋
        state = canonical_form(state)

    return state

# def invalid_moves(state):
#     # return a fixed size binary vector
#     if game_ended(state):
#         return np.zeros(action_size(state))
#     return np.append(state[govars.INVD_CHNL].flatten(), 0)
#
# def valid_moves(state):
#     return 1 - invalid_moves(state)

# def action_size(state=None, board_size: int = None):
#     # return number of actions
#     if state is not None:
#         m, n = state.shape[1:]
#     elif board_size is not None:
#         m, n = board_size, board_size
#     else:
#         raise RuntimeError('No argument passed')
#     return m * n + 1


def prev_player_passed(state):
    return np.max(state[govars.PASS_CHNL] == 1) == 1

# def game_ended(state):
#     """
#     :param state:
#     :return: 0/1 = game not ended / game ended respectively
#     """
#     m, n = state.shape[1:]
#     return int(np.count_nonzero(state[govars.DONE_CHNL] == 1) == m * n)


def turn(state):
    """
    :param state:
    :return: Who's turn it is (govars.BLACK/govars.WHITE)
    """
    return int(np.max(state[govars.TURN_CHNL]))

def canonical_form(state):
    state = np.copy(state)
    if turn(state) == govars.WHITE:
        channels = np.arange(govars.NUM_CHNLS)
        channels[govars.BLACK] = govars.WHITE
        channels[govars.WHITE] = govars.BLACK
        state = state[channels]
        state_utils.set_turn(state)
    return state