import copy
import random
import numpy as np


def rewardMethod(totalNum,stepNum):
    reward = 1.0 + 1/stepNum
    return reward

class TreeNode:
    """蒙特卡洛树节点"""
    def __init__(self, player,action, parent):
        self.player = player
        self.action = action
        self.reward = [0, 0]
        self.n_visits = 0  # 节点被访问的次数
        self.parent = parent  # 节点的父节点
        self.children = set()  # 一个字典，用来存节点的子节点


class MCTS_Mine:
    def __init__(self, n_playout=10000):
        # self.root = TreeNode(None, None)  # 整个蒙特卡洛搜索树的根节点
        self.n_playout = n_playout

    def get_move_by_visits(self,game,player=None):
        game_state = game.game_state_simulator()
        lastPlayer = 1 - game_state.turn()
        current_node = TreeNode(player=lastPlayer, action=None, parent=None)
        for i in range(self.n_playout):
            if not player.valid:
                return -1
            if player is not None:
                player.speed = (i + 1, self.n_playout)
                state = copy.deepcopy(game_state)
                node = current_node

                totalNum = sum(sum(1-state.uselessPosition))
                stepNum = 1

                while not state.game_ended():  # 从根节点一直定位到叶结点
                    stepNum += 1
                    available_actions = state.advanced_valid_move_idcs()
                    if len(available_actions) >= 1:
                        parent = node
                        currentplayer = 1-parent.player
                        action = random.choice(available_actions)
                        state.step(action)
                        try:
                            node = next(node for node in parent.children if node.action == action)
                        except StopIteration:
                            node = TreeNode(currentplayer,action,parent)
                            parent.children.add(node)
                    else:
                        break

                winner = state.winner()

                if winner == -1:  # 和棋
                    reward = [0,0]
                else:
                    if winner == 0:
                        reward = [rewardMethod(totalNum,stepNum),-2*rewardMethod(totalNum,stepNum)]
                    else:
                        reward = [-2*rewardMethod(totalNum, stepNum), rewardMethod(totalNum, stepNum)]

                while node:

                    for index in range(2):
                        node.reward[index] += reward[index] # 黑0白1
                    node.n_visits += 1
                    node = node.parent

        currentPlayer = 1 - lastPlayer

        if current_node.n_visits >= 1:
            children_node = max(
                current_node.children,
                key=lambda node: node.reward[currentPlayer] / float(node.n_visits) if node.n_visits >= 1 else 0)
            action = children_node.action
        else:
            available_actions = game_state.advanced_valid_move_idcs()
            action = random.choice(available_actions)

        for children in current_node.children:
            position = (children.action // 9, children.action % 9)
            print(position, children.n_visits,
                  children.reward[currentPlayer] / float(children.n_visits) if children.n_visits >= 1 else 0)

        return action
