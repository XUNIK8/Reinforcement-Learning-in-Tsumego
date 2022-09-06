import numpy as np
from scipy import ndimage
from scipy.ndimage import measurements

class govars():
    ANYONE = None
    NOONE = -1

    BLACK = 0
    WHITE = 1
    USEL_CHNL = 2
    INVD_CHNL = 3
    TURN_CHNL = 4
    PASS_CHNL = 5
    DONE_CHNL = 6
    NUM_CHNLS = 7

group_struct = np.array([[[0, 0, 0],
                          [0, 0, 0],
                          [0, 0, 0]],
                         [[0, 1, 0],
                          [1, 1, 1],
                          [0, 1, 0]],
                         [[0, 0, 0],
                          [0, 0, 0],
                          [0, 0, 0]]])

surround_struct = np.array([[0, 1, 0],
                            [1, 0, 1],
                            [0, 1, 0]])

neighbor_deltas = np.array([[-1, 0], [1, 0], [0, -1], [0, 1]])

def compute_invalid_moves(state, uselessPosition,player, ko_protect=None):
    """
    Updates invalid moves in the OPPONENT's perspective
    1.) Opponent cannot move at a location
        i.) If it's occupied（被占领的）
        i.) If it's protected by ko
    2.) Opponent can move at a location
        i.) If it can kill
    3.) Opponent cannot move at a location
        i.) If it's adjacent to one of their groups with only one liberty and
            not adjacent to other groups with more than one liberty and is completely surrounded
        ii.) If it's surrounded by our pieces and all of those corresponding groups
            move more than one liberty
    """

    # All pieces and empty spaces
    # 棋盘所有有棋子的分布矩阵，有棋子的位置为1
    all_pieces = np.sum(state[[govars.BLACK, govars.WHITE]], axis=0)
    # 棋盘上所有空交叉点的分布矩阵，空交叉点位置为1
    empties = 1 - all_pieces

    # Setup invalid and valid arrays
    possible_invalid_array = np.zeros(state.shape[1:])
    definite_valids_array = np.zeros(state.shape[1:])

    # Get all groups
    # 上一步落子方各块棋子分布矩阵，及棋子块数
    all_own_groups, num_own_groups = measurements.label(state[player])
    # 下一步落子方各块棋子分布矩阵，及棋子块数
    all_opp_groups, num_opp_groups = measurements.label(state[1 - player])
    expanded_own_groups = np.zeros((num_own_groups, *state.shape[1:]))
    expanded_opp_groups = np.zeros((num_opp_groups, *state.shape[1:]))

    # Expand the groups such that each group is in its own channel
    for i in range(num_own_groups):
        expanded_own_groups[i] = all_own_groups == (i + 1)

    for i in range(num_opp_groups):
        expanded_opp_groups[i] = all_opp_groups == (i + 1)

    # Get all liberties in the expanded form
    # 计算每一块棋子的气分布矩阵
    # 其中np.newaxis == None，matrix[None]意思是在第0维增加一个维度
    # all_own_liberties和all_opp_liberties均是三维矩阵，代表每块棋子的气的分布
    all_own_liberties = empties[np.newaxis] * ndimage.binary_dilation(expanded_own_groups, surround_struct[np.newaxis])
    all_opp_liberties = empties[np.newaxis] * ndimage.binary_dilation(expanded_opp_groups, surround_struct[np.newaxis])

    # all_own_liberties和all_opp_liberties均是三维矩阵， np.sum( , axis=(1,2))针对每块棋子计算其气数
    # own_liberty_counts和opp_liberty_counts均是一维数组，每个元素代表每块棋的气
    own_liberty_counts = np.sum(all_own_liberties, axis=(1, 2))
    opp_liberty_counts = np.sum(all_opp_liberties, axis=(1, 2))

    # Possible invalids are on single liberties of opponent groups and on multi-liberties of own groups
    # Definite valids are on single liberties of own groups, multi-liberties of opponent groups
    # or you are not surrounded
    possible_invalid_array += np.sum(all_own_liberties[own_liberty_counts > 1], axis=0)
    possible_invalid_array += np.sum(all_opp_liberties[opp_liberty_counts == 1], axis=0)

    definite_valids_array += np.sum(all_own_liberties[own_liberty_counts == 1], axis=0)
    definite_valids_array += np.sum(all_opp_liberties[opp_liberty_counts > 1], axis=0)

    # All invalid moves are occupied spaces + (possible invalids minus the definite valids and it's surrounded)
    surrounded = ndimage.convolve(all_pieces, surround_struct, mode='constant', cval=1) == 4
    invalid_moves = all_pieces + possible_invalid_array * (definite_valids_array == 0) * surrounded
    # Ko-protection
    if ko_protect is not None:
        invalid_moves[ko_protect[0], ko_protect[1]] = 1

    invalid_moves += uselessPosition
    # print(invalid_moves)
    return invalid_moves > 0

def update_pieces(state, adj_locs, player):
    opponent = 1 - player
    killed_groups = []

    all_pieces = np.sum(state[[govars.BLACK, govars.WHITE]], axis=0)
    empties = 1 - all_pieces

    all_opp_groups, _ = ndimage.measurements.label(state[opponent])

    # Go through opponent groups
    all_adj_labels = all_opp_groups[adj_locs[:, 0], adj_locs[:, 1]]
    all_adj_labels = np.unique(all_adj_labels)
    for opp_group_idx in all_adj_labels[np.nonzero(all_adj_labels)]:
        opp_group = all_opp_groups == opp_group_idx
        liberties = empties * ndimage.binary_dilation(opp_group)
        if np.sum(liberties) <= 0:
            # Killed group
            opp_group_locs = np.argwhere(opp_group)
            state[opponent, opp_group_locs[:, 0], opp_group_locs[:, 1]] = 0
            killed_groups.append(opp_group_locs)

    return killed_groups

def adj_data(state, action2d, player):
    neighbors = neighbor_deltas + action2d
    valid = (neighbors >= 0) & (neighbors < state.shape[1])
    valid = np.prod(valid, axis=1)
    neighbors = neighbors[np.nonzero(valid)]

    opp_pieces = state[1 - player]
    surrounded = (opp_pieces[neighbors[:, 0], neighbors[:, 1]] > 0).all()

    return neighbors, surrounded

def set_turn(state):
    """
    Swaps turn
    :param state:
    :return:
    """
    state[govars.TURN_CHNL] = 1 - state[govars.TURN_CHNL]