from GymGo import state_utils
from GymGo.state_utils import govars
import goMap # 死活题初始状态
from typing import Union, List, Tuple
import numpy as np
from scipy import ndimage

surround_struct = np.array([[0, 1, 0],
                            [1, 0, 1],
                            [0, 1, 0]])

eye_struct = np.array([[1, 1, 1],
                       [1, 0, 1],
                       [1, 1, 1]])

corner_struct = np.array([[1, 0, 1],
                          [0, 0, 0],
                          [1, 0, 1]])
BLACK = govars.BLACK # 0
WHITE = govars.WHITE # 1


class GoEngine:
    def __init__(self, board_size: int = 9,
                 record_step: int = 4,
                 state_format: str = "separated",
                 record_last: bool = True
                 ):
        """
        围棋引擎初始化

        :param board_size: 棋盘大小，默认为9
        :param komi: 黑棋贴目数，默认黑贴7.5目（3又3/4子）
        :param record_step: 记录棋盘历史状态步数，默认为4
        :param state_format: 记录棋盘历史状态格式
                            【separated：黑白棋子分别记录在不同的矩阵中，[黑棋，白棋，下一步落子方，上一步落子位置(可选)]】
                            【merged：黑白棋子记录在同一个矩阵中，[棋盘棋子分布(黑1白-1)，下一步落子方，上一步落子位置(可选)]】
        :param record_last: 是否记录上一步落子位置
        """
        assert state_format in ["separated", "merged"],\
            "state_format can only be 'separated' or 'merged', but received: {}".format(state_format)

        self.board_size = board_size
        self.record_step = record_step
        self.state_format = state_format
        self.record_last = record_last
        self.current_state = goMap.originalgoMap
        self.survivePlayer = goMap.survivePlayer
        self.originalSurvivePosition = goMap.originalgoMap[self.survivePlayer]
        self.uselessPosition = goMap.originalgoMap[govars.USEL_CHNL]
        # 保存棋盘状态，用于悔棋
        self.board_state_history = []
        # 保存历史动作，用于悔棋
        self.action_history = []

        if state_format == "separated":
            record_step *= 2
        self.state_channels = record_step + 2 if record_last else record_step + 1
        self.board_state = np.zeros((self.state_channels, board_size, board_size))
        self.done = False

    def reset(self) -> np.ndarray:
        """重置current_state, board_state, board_state_history, action_history"""
        self.current_state = goMap.originalgoMap
        self.board_state = np.zeros((self.state_channels, self.board_size, self.board_size))
        self.board_state_history = []
        self.action_history = []
        self.done = False
        return np.copy(self.current_state)


    def step(self, action: Union[List[int], Tuple[int], int, None]) -> np.ndarray:
        """
        围棋落子

        :param action: 下一步落子位置
        :return:
        """
        assert not self.done
        if isinstance(action, tuple) or isinstance(action, list) or isinstance(action, np.ndarray):
            assert 0 <= action[0] < self.board_size
            assert 0 <= action[1] < self.board_size
            action = self.board_size * action[0] + action[1]
        elif isinstance(action, int):
            assert 0 <= action <= self.board_size ** 2
        elif action is None:
            action = self.board_size ** 2

        self.current_state = self.next_state(action, canonical=False)
        # 更新self.board_state
        self.board_state = self._update_state_step(action)
        # 存储历史状态
        self.board_state_history.append(np.copy(self.current_state))
        # 存储历史动作
        self.action_history.append(action)
        self.done = self.game_ended()
        return np.copy(self.current_state)

    def _update_state_step(self, action: int) -> np.ndarray:
        """
        更新self.board_state，须在更新完self.current_state之后更新self.board_state

        :param action: 下一步落子位置，1d-action
        :return:
        """
        if self.state_format == "separated":
            # 根据上一步落子方更新self.board_state(因为self.current_state已经更新完毕)
            if self.turn() == govars.WHITE:
                # 根据更新过后的self.current_state，下一步落子方为白方，则上一步落子方为黑方
                self.board_state[:self.record_step - 1] = np.copy(self.board_state[1:self.record_step])
                self.board_state[self.record_step - 1] = np.copy(self.current_state[govars.BLACK])
            else:
                # 根据更新过后的self.current_state，下一步落子方为黑方，则上一步落子方为白方
                self.board_state[self.record_step: self.record_step * 2 - 1] = \
                    np.copy(self.board_state[self.record_step + 1: self.record_step * 2])
                self.board_state[self.record_step * 2 - 1] = np.copy(self.current_state[govars.WHITE])
        elif self.state_format == "merged":
            self.board_state[:self.record_step - 1] = np.copy(self.board_state[1:self.record_step])
            current_state = self.current_state[[govars.BLACK, govars.WHITE]]
            current_state[govars.WHITE] *= -1
            self.board_state[self.record_step - 1] = np.sum(current_state, axis=0)

        if self.record_last:
            # 更新下一步落子方
            self.board_state[-2] = np.copy(self.current_state[govars.TURN_CHNL])
            # 更新上一步落子位置
            self.board_state[-1] = np.zeros((self.board_size, self.board_size))
            # 上一步不为pass
            if action != self.board_size ** 2:
                # 将action转换成position
                position = action // self.board_size, action % self.board_size
                self.board_state[-1, position[0], position[1]] = 1
        else:
            # 更新下一步落子方
            self.board_state[-1] = np.copy(self.current_state[govars.TURN_CHNL])
        return np.copy(self.board_state)


    def action_valid(self, action) -> bool:
        """判断action是否合法"""
        return self.valid_moves()[action]

    def invalid_moves(self):
        # return a fixed size binary vector
        if self.game_ended():
            return np.zeros(self.action_size(self.current_state))
        return np.append(self.current_state[govars.INVD_CHNL].flatten(), 0)

    def valid_moves(self) -> np.ndarray:
        """下一步落子的有效位置"""
        return 1 - self.invalid_moves()

    def valid_move_idcs(self) -> np.ndarray:
        """下一步落子有效位置的id"""
        valid_moves = self.valid_moves()
        return np.argwhere(valid_moves).flatten()

    def advanced_valid_moves(self):
        """下一步落子的非真眼有效位置"""
        next_player = self.turn()
        valid_moves = 1 - self.current_state[govars.INVD_CHNL]
        eyes_mask = 1 - self.eyes(next_player)
        return np.append((valid_moves * eyes_mask).flatten(), 1)

    def advanced_valid_move_idcs(self) -> np.ndarray:
        """下一步落子的非真眼有效位置的id"""
        advanced_valid_moves = self.advanced_valid_moves()
        return np.argwhere(advanced_valid_moves).flatten()


    def game_ended(self) -> bool:
        """游戏是否结束"""
        """
        :param state:
        :return: 0/1 = game not ended / game ended respectively
        """
        if self.game_ended_by_over() or self.game_ended_by_survived() or self.game_ended_by_killed():
            return True
        else:
            return False

    def game_ended_by_over(self) -> bool:
        m, n = self.current_state.shape[1:]
        done_by_finish = int(np.count_nonzero(self.current_state[govars.DONE_CHNL] == 1) == m * n)
        return done_by_finish

    def game_ended_by_survived(self) -> bool:
        done_by_survived = sum(sum(self.eyes(self.survivePlayer))) >=2
        return done_by_survived

    def game_ended_by_killed(self) -> bool:
        done_by_killed = (sum(sum((self.current_state[self.survivePlayer]*self.originalSurvivePosition)))==0) # <sum(sum(self.originalSurvivePosition))
        return done_by_killed


    def winner(self) -> int:
        """获胜方，游戏未结束返回-1"""
        if not self.done:
            return -1
        else:
            if self.game_ended():
                if self.game_ended_by_killed():
                    winner = 1 - self.survivePlayer
                # elif self.game_ended_by_survived():
                #     winner = self.survivePlayer
                else:
                    winner = self.survivePlayer

            return winner

    # def winning(self):
    #     """
    #     当游戏结束之后，从黑方角度看待，上一步落子后，哪一方胜利
    #     黑胜：1 白胜：-1
    #     """
    #     black_area, white_area = self.areas()
    #     area_difference = black_area - white_area
    #     komi_correction = area_difference - self.komi
    #
    #     return np.sign(komi_correction)

    # def areas(self):
    #     '''
    #     Return black area, white area
    #     '''
    #
    #     all_pieces = np.sum(self.current_state[[govars.BLACK, govars.WHITE]], axis=0)
    #     empties = 1 - all_pieces
    #
    #     empty_labels, num_empty_areas = ndimage.measurements.label(empties)
    #
    #     black_area, white_area = np.sum(self.current_state[govars.BLACK]), np.sum(self.current_state[govars.WHITE])
    #     for label in range(1, num_empty_areas + 1):
    #         empty_area = empty_labels == label
    #         neighbors = ndimage.binary_dilation(empty_area)
    #         black_claim = False
    #         white_claim = False
    #         if (self.current_state[govars.BLACK] * neighbors > 0).any():
    #             black_claim = True
    #         if (self.current_state[govars.WHITE] * neighbors > 0).any():
    #             white_claim = True
    #         if black_claim and not white_claim:
    #             black_area += np.sum(empty_area)
    #         elif white_claim and not black_claim:
    #             white_area += np.sum(empty_area)
    #
    #     return black_area, white_area

    # 查找指定player的眼
    def eyes(self,eyesForPlayer):
        board_shape = self.current_state.shape[1:]
        side_mask = np.zeros(board_shape)
        side_mask[[0, -1], :] = 1
        side_mask[:, [0, -1]] = 1
        nonside_mask = 1 - side_mask
        # eyesForPlayer的棋子分布矩阵
        eyesForPlayer_pieces = self.current_state[eyesForPlayer]
        # 棋盘所有有棋子的分布矩阵，有棋子则相应位置为1
        all_pieces = np.sum(self.current_state[[govars.BLACK, govars.WHITE]], axis=0)
        # 棋盘上所有空交叉点的分布矩阵，空交叉点位置为1
        empties = 1 - all_pieces
        # 对于边角位置
        side_matrix = ndimage.convolve(eyesForPlayer_pieces, eye_struct, mode='constant', cval=1) == 8
        side_matrix = side_matrix * side_mask
        # 对于非边角位置
        nonside_matrix = ndimage.convolve(eyesForPlayer_pieces, surround_struct, mode='constant', cval=1) == 4
        nonside_matrix *= ndimage.convolve(eyesForPlayer_pieces, corner_struct, mode='constant', cval=1) > 2
        nonside_matrix = nonside_matrix * nonside_mask
        return empties * (side_matrix + nonside_matrix)

    def turn(self):
        """
        下一步落子方
        :param state:
        :return: Who's turn it is (govars.BLACK/govars.WHITE)
        """
        return int(np.max(self.current_state[govars.TURN_CHNL]))

    def next_state(self, action1d, canonical=False):
        # Deep copy the state to modify
        current_state = np.copy(self.current_state)

        # Initialize basic variables
        board_shape = current_state.shape[1:]  # state.shape为(通道数, 棋盘高度, 棋盘宽度)
        pass_idx = np.prod(board_shape)  # np.prod()将参数内所有元素连乘，pass_idx："pass"对应的id
        passed = action1d == pass_idx  # 如果action id等于pass_idx，则passed为True
        action2d = action1d // board_shape[0], action1d % board_shape[1]  # 将action1d转换成action2d

        player = self.turn()  # 获取下一步落子方
        previously_passed = self.prev_player_passed(current_state)  # 获取上一步是否为pass
        ko_protect = None

        if passed:
            # We passed
            # 如果下一步为pass，则将next_state中PASS_CHNL矩阵置为全1矩阵
            current_state[govars.PASS_CHNL] = 1
            if previously_passed:
                # Game ended
                # 如果上一步也为pass，则游戏结束【双方连续各pass，则游戏结束】
                # 将next_state中DONE_CHNL矩阵置为全1矩阵
                current_state[govars.DONE_CHNL] = 1
        else:
            # Move was not pass
            current_state[govars.PASS_CHNL] = 0

            # Assert move is valid    检查落子是否有效【state中INVD_CHNL对应位置为0】
            assert current_state[govars.INVD_CHNL, action2d[0], action2d[1]] == 0, ("Invalid move", action2d)

            # Add piece
            current_state[player, action2d[0], action2d[1]] = 1

            # Get adjacent location and check whether the piece will be surrounded by opponent's piece
            # 获取下一步落子位置的相邻位置（仅在棋盘内）、下一步落子位置是否被下一步落子方对手的棋子包围
            adj_locs, surrounded = state_utils.adj_data(current_state, action2d, player)

            # Update pieces
            # 更新棋盘黑白棋子分布矩阵，并返回各组被杀死的棋子列表
            killed_groups = state_utils.update_pieces(current_state, adj_locs, player)

            # If only killed one group, and that one group was one piece, and piece set is surrounded,
            # activate ko protection
            if len(killed_groups) == 1 and surrounded:
                killed_group = killed_groups[0]
                if len(killed_group) == 1:
                    ko_protect = killed_group[0]

        # Update invalid moves

        current_state[govars.INVD_CHNL] = state_utils.compute_invalid_moves(current_state, self.uselessPosition, player, ko_protect)

        # Switch turn
        # 设置下一步落子方
        state_utils.set_turn(current_state)

        # 该标记是选择是否始终以黑棋视角看待当前游戏局面
        if canonical:
            # Set canonical form
            # 该函数将黑白棋子分布对换，并更改下一手落子方为黑棋
            current_state = self.canonical_form(current_state)

        return current_state

    def prev_player_passed(self,state):
        return np.max(state[govars.PASS_CHNL] == 1) == 1

    def canonical_form(self,state):
        state = np.copy(state)
        if self.turn(state) == govars.WHITE:
            channels = np.arange(govars.NUM_CHNLS)
            channels[govars.BLACK] = govars.WHITE
            channels[govars.WHITE] = govars.BLACK
            state = state[channels]
            state_utils.set_turn(state)
        return state

    def action_size(self,state=None, board_size: int = None):
        # return number of actions
        if state is not None:
            m, n = state.shape[1:]
        elif board_size is not None:
            m, n = board_size, board_size
        else:
            raise RuntimeError('No argument passed')
        return m * n + 1
