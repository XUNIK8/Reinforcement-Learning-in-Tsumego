
import numpy as np
import pandas as pd
import copy
from operator import itemgetter


rewardRate = 1 # 回报1+rewardRate/stepNum
punishRate = 3 # 惩罚倍数
declineRate = 0.9 # 衰减系数
c_puct = 5 # UCB权重

def rewardMethod(totalNum,stepNum):
    reward = 1.0 + rewardRate/stepNum
    return reward

# def softmax(x):
#     probs = np.exp(x - np.max(x))
#     probs /= np.sum(probs)
#     return probs


def evaluate_rollout(simulate_game_state, rollout_policy_fn, limit=1000):
    """
    使用rollout_policy_fn玩游戏直至游戏结束或达到限制数，如果当前玩家获胜，则返回+1，对手胜则返回-1，和棋则返回0
    如果模拟次数超过限制游戏还没结束，则同样返回0

    :param simulate_game_state: 模拟游戏状态
    :param rollout_policy_fn: 产生下一步各合法动作及其概率的函数
    :param limit: 限制模拟步数，超过这个限制还没结束，游戏视为和棋
    :return:
    """
    game_state_copy = copy.deepcopy(simulate_game_state)
    totalNum = sum(sum(1 - simulate_game_state.uselessPosition))
    player = game_state_copy.turn()
    stepNum = 0
    for _ in range(limit):
        stepNum += 1
        end, winner = game_state_copy.game_ended(), game_state_copy.winner()
        if end:
            break
        action_probs = rollout_policy_fn(game_state_copy)
        max_action = max(action_probs, key=itemgetter(1))[0]
        game_state_copy.step(max_action)
    else:
        winner = -1
    if winner == -1:  # 和棋
        return 0
    else:
        return rewardMethod(totalNum,stepNum) if winner == player else -punishRate*rewardMethod(totalNum,stepNum)
        # return rewardMethod(totalNum,stepNum) if winner == player else -5*rewardMethod(totalNum,stepNum)


class TreeNode:
    """蒙特卡洛树节点"""
    def __init__(self, parent, prior_p):
        self.parent = parent  # 节点的父节点
        self.children = {}  # 一个字典，用来存节点的子节点
        self.n_visits = 0  # 节点被访问的次数
        self.Q = 0  # 节点的平均行动价值
        self.U = 0  # MCTS选择Q+U最大的节点，公式里的U
        self.P = prior_p  # 节点被选择的概率

    def select(self, c_puct):
        """
        蒙特卡洛树搜索的第一步：选择
        蒙特卡洛树搜索通过不断选择 最大上置信限Q+U 的子节点，直至一个树的叶结点
        该函数为进行一步选择函数

        :param c_puct: 为计算U值公式中的c_puct，是一个决定探索水平的常数
        :return: 返回一个元组(action, next_node)
        """
        return max(self.children.items(),
                   key=lambda act_node: act_node[1].get_value(c_puct))

    def expand(self, action_priors):
        """
        当select搜索到一个叶结点，且该叶节点代表的局面游戏没有结束，
        需要expand树，创建一系列可能得节点，即对应节点所有可能选择的动作对应的子节点

        :param action_priors: 为一个列表，列表中的每一个元素为一个 特定动作及其先验概率 的元组
        :return:
        """
        for action, prob in action_priors:
            if action not in self.children:
                self.children[action] = TreeNode(self, prob)

    def update(self, leaf_value):
        """
        根据子树的价值更新当前节点的价值

        :param leaf_value: 以当前玩家的视角看待得到的子树的价值
        :return:
        """
        self.n_visits += 1  # 当前节点的访问次数+1
        # 更新当前节点的Q值，下述公式可由Q =  W / N 推导得到
        # Q_old = W_old / N_old
        # Q = (W_old + v) / (N_old + 1) = (Q_old * N_old + v) / (N_old + 1)
        self.Q += 1.0 * (leaf_value - self.Q) / self.n_visits

    def update_recursive(self, leaf_value):
        """
        跟心所有祖先的Q值及访问次数

        :param leaf_value:
        :return:
        """
        if self.parent:  # 如果有父节点，证明还没到根节点
            leaf_value *= declineRate
            self.parent.update_recursive(-leaf_value)  # -leaf_value是因为每向上一层，以当前玩家视角，价值反转
        self.update(leaf_value)

    def get_value(self, c_puct):
        """
        计算并返回一个节点的 上置信限 评价，即Q+U值

        :param c_puct: 为计算U值公式中的c_puct，是一个决定探索水平的常数
        :return:
        """
        self.U = c_puct * self.P * np.sqrt(self.parent.n_visits) / (1 + self.n_visits)
        return self.Q + self.U

    def is_leaf(self):
        """
        判断当前节点是否为叶结点。、

        :return:
        """
        return self.children == {}

    def is_root(self):
        """
        判断当前节点是否为根节点

        :return:
        """
        return self.parent is None


class MCTS_Alpha:
    """蒙特卡洛树搜索主体"""
    def __init__(self, policy_value_fn, n_playout=10000):
        self.root = TreeNode(None, 1.0)  # 整个蒙特卡洛搜索树的根节点
        # policy_value_fn是一个函数，该函数的输入为game_state，
        # 输出为一个列表，列表中的每一个元素为(action, probability)形式的元组
        self.policy = policy_value_fn
        # c_puct为一个正数，用于控制多块收敛到策略的最大值。这个数越大，意味着越依赖前面的结果。
        self.c_puct = c_puct
        self.n_playout = n_playout

    def playout(self, simulate_game_state):
        """
        从根节点不断选择直到叶结点，并获取叶结点的值，反向传播到叶结点的祖先节点

        :param simulate_game_state: 模拟游戏对象
        :return:
        """
        node = self.root
        totalNum = sum(sum(1-simulate_game_state.uselessPosition))
        stepNum = 0
        while True:  # 从根节点一直定位到叶结点
            stepNum += 1
            if node.is_leaf():
                break
            # 贪婪地选择下一步动作
            action, node = node.select(self.c_puct)
            simulate_game_state.step(action)
        # 使用网络来评估叶结点，产生一个每一个元素均为(action, probability)元组的列表，以及
        # 一个以当前玩家视角看待的在[-1, 1]之间的v值
        action_probs, leaf_value = self.policy(simulate_game_state)
        # 检查模拟游戏是否结束
        end, winner = simulate_game_state.game_ended(), simulate_game_state.winner()
        if not end:  # 没结束则扩展
            node.expand(action_probs)
        else:
            if winner == -1:  # 和棋
                leaf_value = 0.0
            else:
                leaf_value = (
                    rewardMethod(totalNum,stepNum) if winner == simulate_game_state.turn() else -punishRate*rewardMethod(totalNum,stepNum)
                )
        # 更新此条遍历路径上的节点的访问次数和value
        # 这里的值要符号反转，因为这个值是根据根节点的player视角来得到的
        # 但是做出下一步落子的是根节点对应player的对手
        node.update_recursive(-leaf_value)


    def get_move_by_visits(self, game, player=None):
        """
        执行n_playout次模拟，返回访问次数最多的动作

        :param game: 游戏模拟器
        :param player: 调用该函数的player，用于进行进度绘制
        :return: 返回访问次数最多的动作
        """
        for i in range(self.n_playout):
            if not player.valid:
                return -1
            if player is not None:
                player.speed = (i + 1, self.n_playout)
            game_state = game.game_state_simulator()
            self.playout(game_state)

        ### 参数
        parameters = [rewardRate,declineRate,punishRate]
        ### 正确动作的位次
        visits = []
        actions = []
        for children in self.root.children.items():
            visits.append(children[1].n_visits)
            actions.append(children[0])
        rk=pd.Series(visits,index=actions)
        rk=rk.rank(method='min',ascending=False)
        for children in self.root.children.items():
            rank = rk[children[0]]
            print((children[0]//9,children[0]%9),children[1].n_visits/self.n_playout,rank)

        
        return max(self.root.children.items(), key=lambda act_node: act_node[1].n_visits)[0]

    def update_with_move(self, last_move):
        """
        蒙特卡洛搜索树向深层前进一步，并且保存对应子树的全部信息

        :param last_move: 上一步选择的动作
        :return:
        """
        if last_move in self.root.children:
            self.root = self.root.children[last_move]
            self.root.parent = None
        else:
            self.root = TreeNode(None, 1.0)
