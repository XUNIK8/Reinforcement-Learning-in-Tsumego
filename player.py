
from threading import Thread
import numpy as np
from time import sleep
from mcts_alpha import MCTS_Alpha, evaluate_rollout
from mcts_mine import MCTS_Mine

class Player:
    def __init__(self):
        # 是否允许启动线程计算下一步action标记
        self.allow = True
        # 下一步action
        self.action = None
        # Player名字
        self.name = 'Player'
        # 该Player是否有效，用于提前退出计算循环
        self.valid = True
        # 表明落子计算进度的量(仅在Player为MCTS或AlphaGo时生效)
        self.speed = None


    def play(self, game):
        if self.allow and self.action is None:
            self.allow = False
            # daemon=True可以使得主线程结束时，所有子线程全部退出，使得点击退出游戏按钮后，不用等待子线程结束
            Thread(target=self.step, args=(game, ), daemon=True).start()

    def step(self, game):
        """
        根据当前游戏状态，获得执行动作
        :param game: 游戏模拟器对象
        :return:
        """
        print('Hello!')


class HumanPlayer(Player):
    def __init__(self):
        super().__init__()
        self.name = '人类玩家'

class RandomPlayer(Player):
    def __init__(self):
        super().__init__()
        self.name = '随机落子'

    def step(self, game):
        sleep(1)
        self.action = self.get_action(game)

    @staticmethod
    def get_action(game):
        valid_move_idcs = game.game_state.advanced_valid_move_idcs()
        if len(valid_move_idcs) > 1:
            valid_move_idcs = valid_move_idcs[:-1]
        action = np.random.choice(valid_move_idcs)
        return action

class MCTSPlayer_Alpha(Player):
    def __init__(self, n_playout=20):
        super().__init__()
        self.name = '蒙特卡洛zero{}'.format(n_playout)

        def rollout_policy_fn(game_state_simulator):
            # 选择随机动作
            availables = game_state_simulator.advanced_valid_move_idcs() # advanced_valid_move_idcs
            action_probs = np.random.rand(len(availables))
            return zip(availables, action_probs)

        def policy_value_fn(game_state_simulator):
            # 返回均匀概率及通过随机方法获得的节点价值
            availables = game_state_simulator.advanced_valid_move_idcs() # advanced_valid_move_idcs
            action_probs = np.ones(len(availables)) / len(availables)
            return zip(availables, action_probs), evaluate_rollout(game_state_simulator, rollout_policy_fn)

        # alphagozero
        self.mcts = MCTS_Alpha(policy_value_fn, n_playout)

    def step(self, game):
        action= self.get_action(game)
        if action == -1:
            action = None
            self.allow = True
        self.action = action
        
        # 获得动作后将速度区域清空
        self.speed = (0, 1)

    def reset_player(self):
        self.mcts.update_with_move(-1)

    def get_action(self, game):

        move = self.mcts.get_move_by_visits(game, self)
        self.mcts.update_with_move(-1)
        return move

class MCTSPlayer_Mine(Player):
    def __init__(self,n_playout=20):
        super().__init__()
        self.name = '蒙特卡洛new{}'.format(n_playout)

        # gomain
        self.mcts = MCTS_Mine(n_playout)

    def step(self, game):
        action = self.get_action(game)
        if action == -1:
            action = None
            self.allow = True
        self.action = action

        # 获得动作后将速度区域清空
        self.speed = (0, 1)

    def reset_player(self):
        pass

    def get_action(self, game):

        move = self.mcts.get_move_by_visits(game, self)
        #move = self.mcts.get_move_by_probs(game,self)
        return move