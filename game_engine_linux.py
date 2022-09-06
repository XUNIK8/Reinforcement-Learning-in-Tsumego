
import sys
import copy
from pygame import init

from pytest import param
import go_engine
from go_engine import GoEngine
from player import *
from typing import List, Tuple, Callable, Union
import time
import pandas as pd


class GameEngine:
    def __init__(self,
                 board_size: int = 9,
                 record_step: int = 4,
                 state_format: str = "separated",
                 record_last: bool = True):
        """
        游戏引擎初始化

        :param board_size: 棋盘大小，默认为9
        :param komi: 黑棋贴目数，默认黑贴7.5目（3又3/4子）
        :param record_step: 记录棋盘历史状态步数，默认为4
        :param state_format: 记录棋盘历史状态格式
                            【separated：黑白棋子分别记录在不同的矩阵中，[黑棋，白棋，下一步落子方，上一步落子位置(可选)]】
                            【merged：黑白棋子记录在同一个矩阵中，[棋盘棋子分布(黑1白-1)，下一步落子方，上一步落子位置(可选)]】
        :param record_last: 是否记录上一步落子位置
        """
        assert board_size in [9, 13, 19]
        assert state_format in ["separated", "merged"]

        self.board_size = board_size
        self.record_step = record_step
        self.state_format = state_format
        self.record_last = record_last

        # 初始化GoEngine
        self.game_state = GoEngine(board_size=board_size,
                                   record_step=record_step,
                                   state_format=state_format,
                                   record_last=record_last)


        # 游戏控制状态
        self.play_state = False

        # 黑方玩家
        self.black_player = HumanPlayer()
        # 白方玩家
        self.white_player = HumanPlayer()
        # 黑方玩家ID
        self.black_player_id = 0
        # 白方玩家ID
        self.white_player_id = 0



    def take_action(self):
        """
        1. 控制self.black_player和self.white_player产生下一步的action
        2. 当self.black_player.action或self.white_player.action不为None时候，执行相应动作
        3. 当self.black_player.speed或self.white_player.speed不为None，绘制当前落子进度动画
        4. 更新所有激活的tools
        """
        # 计算下一步action

        if self.play_state and self.game_state.turn() == go_engine.BLACK and \
                not isinstance(self.black_player, HumanPlayer):
            self.black_player.step(self)
        elif self.play_state and self.game_state.turn() == go_engine.WHITE and \
                not isinstance(self.white_player, HumanPlayer):
            self.white_player.step(self)

        # 执行action
        if self.play_state and self.game_state.turn(
        ) == go_engine.BLACK and self.black_player.action is not None:
            self.game_state.step(self.black_player.action)
            action = self.white_player.action
            self.black_player.action = None
            self.white_player.allow = True
        elif self.play_state and self.game_state.turn(
        ) == go_engine.WHITE and self.white_player.action is not None:
            self.game_state.step(self.white_player.action)
            action = self.white_player.action
            self.white_player.action = None
            self.black_player.allow = True
        else:
            action = None
        return action

    def game_state_simulator(self, train=False) -> GoEngine:
        """返回一个用作模拟的game_state"""
        game_state = GoEngine(board_size=self.board_size,
                              record_step=self.record_step,
                              state_format=self.state_format,
                              record_last=self.record_last)

        game_state.current_state = np.copy(self.game_state.current_state)
        game_state.board_state = np.copy(self.game_state.board_state)
        game_state.board_state_history = copy.copy(
            self.game_state.board_state_history)
        game_state.action_history = copy.copy(self.game_state.action_history)
        game_state.done = self.game_state.done

        return game_state

    @staticmethod
    def create_player(player_id,c_puct, rewardRate,punishRate,declineRate) -> Player:
        """根据player_id创建player"""
        n_playout = 400 * (player_id - 1)
        if player_id == 0:
            player = HumanPlayer()
        elif player_id == 1:
            player = RandomPlayer()
        elif player_id in [2, 3, 4, 5, 6]:
            player = MCTSPlayer_Alpha(n_playout,c_puct, rewardRate,punishRate,declineRate)
        elif player_id in [7, 8, 9, 10, 11]:
            player = MCTSPlayer_Mine(n_playout=400 * (player_id - 6))
        else:
            player = Player()
        return player

    def fct_for_black_player(self):
        # 切换玩家，会使游戏暂停
        self.play_state = False
        # 被切换掉的玩家对象失效
        self.black_player.valid = False

        self.black_player_id += 1
        # player_num为游戏支持的Player总数
        player_num = 12
        self.black_player_id %= player_num

        # 将当前Player设置为响应Player
        self.black_player = self.create_player(self.black_player_id,c_puct, rewardRate,punishRate,declineRate)

    def fct_for_white_player(self):
        # 切换玩家，会使游戏暂停
        self.play_state = False
        self.white_player.valid = False

        self.white_player_id += 1
        # player_num为游戏支持的Player总数
        player_num = 12
        self.white_player_id %= player_num

        # 将当前Player设置为响应Player
        self.white_player = self.create_player(self.white_player_id,c_puct, rewardRate,punishRate,declineRate)

    def fct_for_play_game(self):
        # 当开始游戏按钮被点击
        if self.play_state:

            # 游戏在进行状态时点击该按钮，游戏进入暂停状态
            self.play_state = False
            # 切换至暂停状态，退出落子action计算循环
            self.next_player().valid = False
        else:
            # 游戏在未进行状态时点击该按钮
            if self.game_state.done:
                self.game_state.reset()
                self.black_player.allow = True
            else:
                self.next_player().valid = True
            self.play_state = True

    def fct_for_pass(self):
        # pass一手
        # 仅在游戏开始且当前玩家为HumanPlayer时有效
        if self.play_state:
            next_player = self.next_player()
            if isinstance(next_player, HumanPlayer):
                if self.game_state.turn() == go_engine.BLACK:
                    self.black_player.action = self.board_size**2
                else:
                    self.white_player.action = self.board_size**2

    def fct_for_regret(self):
        # 悔棋
        if self.play_state:
            next_player = self.next_player()

            if len(self.game_state.board_state_history) > 2:
                self.game_state.current_state = self.game_state.board_state_history[
                    -3]
                self.game_state.board_state_history = self.game_state.board_state_history[:
                                                                                          -2]
                action = self.game_state.action_history[-3]
                self.game_state.action_history = self.game_state.action_history[:
                                                                                -2]
                

            elif len(self.game_state.board_state_history) == 2:
                self.game_state.reset()


    def fct_for_restart(self,c_puct, rewardRate,punishRate,declineRate):
        # 当重新开始按钮被点击
        self.play_state = True

        self.black_player.valid = False
        self.white_player.valid = False
        self.black_player = self.create_player(self.black_player_id,c_puct, rewardRate,punishRate,declineRate)
        self.white_player = self.create_player(self.white_player_id,c_puct, rewardRate,punishRate,declineRate)

        self.game_state.reset()


    def fct_for_new_game(self):
        self.black_player.valid = False
        self.white_player.valid = False

        # 初始化
        new_game_size = 9 if self.board_size == 13 else 13
        self.__init__(new_game_size,
                      record_step=self.record_step,
                      state_format=self.state_format,
                      record_last=self.record_last)

    @staticmethod
    def fct_for_exit():
        # 当退出游戏按钮被点击
        sys.exit()

    def next_player(self):
        """返回下一步落子方玩家对象"""
        if self.game_state.turn() == go_engine.BLACK:
            return self.black_player
        else:
            return self.white_player

class parameters():
    def __init__(self, c_puct, rewardRate,punishRate,declineRate):
        self.c_puct = c_puct # UCB权重
        self.rewardRate = rewardRate # 回报1+rewardRate/stepNum
        self.punishRate = punishRate # 惩罚倍数
        self.declineRate = declineRate # 衰减系数
    def c_puct(self):
        return self.c_puct
    def rewardRate(self):
        return rewardRate # 回报1+rewardRate/stepNum
    def punishRate(self):
        return punishRate # 惩罚倍数
    def declineRate(self):
        return declineRate # 衰减系数#


if __name__ == '__main__':

    game = GameEngine()
    c_puctList = [3,5,10]
    rewardRateList = [1,5,10]
    punishRateList = [1,3,5]
    declineRateList = [1,0.9,0.8]
    for c_puct in c_puctList:
        for rewardRate in rewardRateList:
            for punishRate in punishRateList:
                for declineRate in declineRateList:
                    
                    ntimes = 1
                    
                    result = {'parameters':[],'id':[],'count':[],'topcount':[],'ranks':[],'actions':[],'time':[]}
                    startTime = time.time()
                    for id in range(4, 7):
                        idStartTime = time.time()
                        n = 0
                        count = 0
                        topcount = 0

                        game.white_player = game.create_player(id,c_puct, rewardRate,punishRate,declineRate) #
                        game.white_player_id = id
                        result['id'].append(id)
                    
                        actionList =[]
                        rankList = []
                        # 设置实验次数
                        while n < ntimes:
                            
                            n += 1
                            game.fct_for_play_game()
                    
                            while True:
                                action = game.take_action()
                                if action is not None: #
                                    break
                    
                            if action == 9: #
                                count += 1

                            rank = game.white_player.rank #
                            if rank <3:
                                topcount += 1
                            parameters = game.white_player.parameters
                            rankList.append(rank) #

                            row = action // game.board_size #
                            column = action % game.board_size #
                            position = (row,column)
                            actionList.append(position)

                            print('算法',id,'第',n,'轮',position)
                            game.fct_for_restart(c_puct, rewardRate,punishRate,declineRate)
                            game.fct_for_play_game()
                    
                        result['parameters'].append(parameters)
                        result['ranks'].append(rankList) #

                        result['count'].append(count)
                        result['topcount'].append(topcount)
                        result['actions'].append(actionList)
                        timeSpent = round((time.time() - idStartTime) / ntimes,2)
                        result['time'].append(timeSpent)

                        print('Stats:',id,count,topcount,actionList,timeSpent)
                        
                    
                    print('Time:', round(time.time() - startTime,2))
                    print('Final Result:',result)
                    df = pd.DataFrame(result)
                    df.to_csv('result.csv',mode='a', index=False)
    game.fct_for_exit()