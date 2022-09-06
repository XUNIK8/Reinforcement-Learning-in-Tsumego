import pygame
import sys
import copy

from pytest import param
import go_engine
from go_engine import GoEngine
from pgutils.manager import Manager
from pgutils.pgcontrols.button import Button
from pgutils.text import draw_text
from pgutils.pgtools.information_display import InformationDisplay
from pgutils.position import pos_in_surface
from player import *
from typing import List, Tuple, Callable, Union
import time
import pandas as pd

SCREEN_SIZE = 1.5  # 控制模拟器界面放大或缩小的比例
SCREENWIDTH = int(SCREEN_SIZE * 600)  # 屏幕宽度
SCREENHEIGHT = int(SCREEN_SIZE * 400)  # 屏幕高度
BGCOLOR = (50, 110, 162)  # 屏幕背景颜色
BOARDCOLOR = (210, 123, 1)  # 棋盘颜色
BLACK = (0, 0, 0)  # 黑色
WHITE = (255, 255, 255)  # 白色
MARKCOLOR = (0, 255, 255)  # 最近落子标记颜色

# pygame初始化
pygame.init()
# 创建游戏主屏幕
SCREEN = pygame.display.set_mode((SCREENWIDTH, SCREENHEIGHT))
# 设置游戏名称
pygame.display.set_caption('TsumeGo')
# 启动界面绘制启动信息
loading_font = pygame.font.Font('assets/fonts/msyh.ttc', 56)
loading_text_render = loading_font.render('正在加载...', True, WHITE)
SCREEN.blit(loading_text_render,
            ((SCREEN.get_width() - loading_text_render.get_width()) / 2,
             (SCREEN.get_height() - loading_text_render.get_height()) / 2))
pygame.display.update()

IMAGES = {
    'black':
    (pygame.image.load('assets/pictures/B-9-new.png').convert_alpha(),
     pygame.image.load('assets/pictures/B-13-new.png').convert_alpha(),
     pygame.image.load('assets/pictures/B-19-new.png').convert_alpha()),
    'white':
    (pygame.image.load('assets/pictures/W-9-new.png').convert_alpha(),
     pygame.image.load('assets/pictures/W-13-new.png').convert_alpha(),
     pygame.image.load('assets/pictures/W-19-new.png').convert_alpha())
}
SOUNDS = {
    'stone': pygame.mixer.Sound('assets/audios/Stone.wav'),
    'button': pygame.mixer.Sound('assets/audios/Button.wav')
}


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

        # 初始化pygame控件及工具管理器
        self.manager = Manager()
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

        # 填充背景色
        SCREEN.fill(BGCOLOR)
        # 棋盘区域
        self.board_surface = SCREEN.subsurface(
            (0, 0, SCREENHEIGHT, SCREENHEIGHT))
        # 展示落子进度的区域
        self.speed_surface = SCREEN.subsurface(
            (SCREENHEIGHT, 0, 5, SCREENHEIGHT))
        # 玩家控制区域
        self.pmc_surface = SCREEN.subsurface(
            (SCREENHEIGHT + self.speed_surface.get_width(), 0,
             SCREENWIDTH - SCREENHEIGHT - self.speed_surface.get_width(),
             SCREENHEIGHT / 4))
        # 游戏操作区域区域
        self.operate_surface = SCREEN.subsurface(
            (SCREENHEIGHT + self.speed_surface.get_width(),
             self.pmc_surface.get_height(),
             SCREENWIDTH - SCREENHEIGHT - self.speed_surface.get_width(),
             SCREENHEIGHT - self.pmc_surface.get_height()))

        # 初始化按钮控件
        pmc_button_texts = [self.black_player.name, self.white_player.name]
        pmc_button_call_functions = [
            self.fct_for_black_player, self.fct_for_white_player
        ]
        self.pmc_buttons = self.create_buttons(
            self.pmc_surface,
            pmc_button_texts,
            pmc_button_call_functions, [self.pmc_surface.get_width() / 3, 40],
            70,
            up_color=[202, 171, 125],
            down_color=[186, 146, 86],
            outer_edge_color=[255, 255, 214],
            size=[160, 40],
            font_size=18,
            inner_edge_color=[247, 207, 181],
            text_color=[253, 253, 19])
        operate_play_button_texts = [
            '开始游戏', '弃子', '悔棋', '重新开始',
            ('十三' if self.board_size == 9 else '九') + '路棋', '退出游戏'
        ]
        operate_play_button_call_functions = [
            self.fct_for_play_game, self.fct_for_pass, self.fct_for_regret,
            self.fct_for_restart, self.fct_for_new_game, self.fct_for_exit
        ]
        self.operate_play_buttons = self.create_buttons(
            self.operate_surface,
            operate_play_button_texts,
            operate_play_button_call_functions, ['center', 70],
            60,
            size=[180, 40],
            font_size=16)

        # 按钮控件注册
        self.manager.control_register(self.pmc_buttons)
        self.manager.control_register(self.operate_play_buttons)

        # 棋盘每格的大小
        self.block_size = int(SCREEN_SIZE * 360 / (self.board_size - 1))
        # 棋子大小
        if self.board_size == 9:
            self.piece_size = IMAGES['black'][0].get_size()
        elif self.board_size == 13:
            self.piece_size = IMAGES['black'][1].get_size()
        else:
            self.piece_size = IMAGES['black'][2].get_size()

        # 绘制棋盘、PMC区域、操作区域
        self.draw_board()
        self.draw_pmc()
        self.draw_operate()

        # 刷新屏幕
        pygame.display.update()

    def draw_board(self):
        """绘制棋盘"""
        # 背景颜色覆盖
        self.board_surface.fill(BOARDCOLOR)
        # 确定棋盘边框坐标
        rect_pos = (int(SCREEN_SIZE * 20), int(SCREEN_SIZE * 20),
                    int(SCREEN_SIZE * 360), int(SCREEN_SIZE * 360))
        # 绘制边框
        pygame.draw.rect(self.board_surface, BLACK, rect_pos, 3)
        # 绘制棋盘内线条
        for i in range(self.board_size - 2):
            pygame.draw.line(self.board_surface, BLACK,
                             (SCREEN_SIZE * 20, SCREEN_SIZE * 20 +
                              (i + 1) * self.block_size),
                             (SCREEN_SIZE * 380, SCREEN_SIZE * 20 +
                              (i + 1) * self.block_size), 2)
            pygame.draw.line(self.board_surface, BLACK,
                             (SCREEN_SIZE * 20 +
                              (i + 1) * self.block_size, SCREEN_SIZE * 20),
                             (SCREEN_SIZE * 20 +
                              (i + 1) * self.block_size, SCREEN_SIZE * 380), 2)
        # 绘制天元和星位
        if self.board_size == 9:
            position_loc = [2, 4, 6]
        elif self.board_size == 13:
            position_loc = [3, 6, 9]
        else:
            position_loc = [3, 9, 15]
        positions = [[
            SCREEN_SIZE * 20 + 1 + self.block_size * i,
            SCREEN_SIZE * 20 + 1 + self.block_size * j
        ] for i in position_loc for j in position_loc]
        for pos in positions:
            pygame.draw.circle(self.board_surface, BLACK, pos, 5, 0)

    def draw_pmc(self):
        self.pmc_surface.fill(BGCOLOR)
        # 绘制4行说明文字
        texts = ['黑方', '白方']
        pos_next = [self.pmc_surface.get_width() / 8, 40]
        for text in texts:
            pos_next = draw_text(self.pmc_surface,
                                 text,
                                 pos_next,
                                 font_size=25,
                                 next_bias=(0, 40))

        # 按钮激活
        for button in self.pmc_buttons:
            button.enable()

    def draw_over(self):
        """绘制游戏结束画面"""
        # 获得黑白双方的区域
        winner = self.game_state.winner()
        if winner == -1:
            over_text = '平局'
        elif winner == 0:
            over_text = '黑胜'
        else:
            over_text = '白胜'

        over_screen = pygame.Surface((320, 170), pygame.SRCALPHA)
        over_screen.fill((57, 44, 33, 100))
        draw_text(over_screen,
                  over_text, ['center', 'center'],
                  font_size=26,
                  font_color=[220, 220, 220])
        self.board_surface.blit(
            over_screen,
            ((self.board_surface.get_width() - over_screen.get_width()) / 2,
             (self.board_surface.get_height() - over_screen.get_height()) / 2))

    def draw_speed(self, count, total):
        """一个简单绘制落子进度的方法"""
        self.speed_surface.fill(BGCOLOR)
        sub_speed_area = self.speed_surface.subsurface(
            (0, SCREENHEIGHT - round(count / total * SCREENHEIGHT),
             self.speed_surface.get_width(),
             round(count / total * SCREENHEIGHT)))
        sub_speed_area.fill((15, 255, 255))

    def draw_operate(self):
        self.operate_surface.fill(BGCOLOR)
        self.operate_surface.fill(BGCOLOR)
        # 按钮激活
        for button in self.operate_play_buttons:
            button.enable()

    def draw_pieces(self) -> None:
        """绘制棋子方法"""
        game_state = self.game_state

        for i in range(self.board_size):
            for j in range(self.board_size):
                # 确定绘制棋子的坐标
                pos = (SCREEN_SIZE * 22 + self.block_size * j -
                       self.piece_size[1] / 2, SCREEN_SIZE * 19 +
                       self.block_size * i - self.piece_size[0] / 2)
                # 查看相应位置有无黑色棋子或白色棋子
                if game_state.current_state[go_engine.BLACK][i, j] == 1:
                    if self.board_size == 9:
                        self.board_surface.blit(IMAGES['black'][0], pos)
                    elif self.board_size == 13:
                        self.board_surface.blit(IMAGES['black'][1], pos)
                    else:
                        self.board_surface.blit(IMAGES['black'][2], pos)
                elif game_state.current_state[go_engine.WHITE][i, j] == 1:
                    if self.board_size == 9:
                        self.board_surface.blit(IMAGES['white'][0], pos)
                    elif self.board_size == 13:
                        self.board_surface.blit(IMAGES['white'][1], pos)
                    else:
                        self.board_surface.blit(IMAGES['white'][2], pos)

    def draw_mark(self, action):
        """根据最近落子的棋盘坐标，绘制标记"""
        # 仅在action不为pass时生效
        if action != self.board_size**2:
            game_state = self.game_state

            row = action // self.board_size
            col = action % self.board_size
            if game_state.turn() == go_engine.WHITE:
                if self.board_size == 9:
                    pos = (SCREEN_SIZE * 19 + col * self.block_size,
                           SCREEN_SIZE * 22 + row * self.block_size)
                elif self.board_size == 13:
                    pos = (SCREEN_SIZE * 20 + col * self.block_size,
                           SCREEN_SIZE * 21 + row * self.block_size)
                else:
                    pos = (SCREEN_SIZE * 21 + col * self.block_size,
                           SCREEN_SIZE * 20 + row * self.block_size)
            else:
                if self.board_size == 9:
                    pos = (SCREEN_SIZE * 19 + col * self.block_size,
                           SCREEN_SIZE * 20 + row * self.block_size)
                elif self.board_size == 13:
                    pos = (SCREEN_SIZE * 20 + col * self.block_size,
                           SCREEN_SIZE * 20 + row * self.block_size)
                else:
                    pos = (SCREEN_SIZE * 21 + col * self.block_size,
                           SCREEN_SIZE * 19 + row * self.block_size)
            pygame.draw.circle(self.board_surface, MARKCOLOR, pos,
                               self.piece_size[0] / 2 + 2 * SCREEN_SIZE, 2)

    def play_step(self, action):
        """输入动作，更新game_state状态，并在界面上绘制相应的动画"""
        self.game_state.step(action)
        currentPlayer = '白棋' if self.game_state.turn() == 0 else '黑棋'
        # 重绘棋盘、棋子、落子标记
        if isinstance(action, tuple) or isinstance(action, list) or isinstance(
                action, np.ndarray):
            assert 0 <= action[0] < self.board_size
            assert 0 <= action[1] < self.board_size
            action = self.board_size * action[0] + action[1]
        if action != self.board_size**2 and action is not None:

            row = action // self.board_size
            column = action % self.board_size
            print(currentPlayer, row, column)

            self.draw_board()
            self.draw_pieces()
            self.draw_mark(action)
            SOUNDS['stone'].play()
        else:
            self.draw_board()
            self.draw_pieces()
            print(currentPlayer, ':Pass')

            over_text = currentPlayer + 'PASS'
            over_screen = pygame.Surface((320, 110), pygame.SRCALPHA)
            over_screen.fill((57, 44, 33, 100))
            draw_text(over_screen,
                      over_text, ['center', 'center'],
                      font_size=26,
                      font_color=[220, 220, 220])
            self.board_surface.blit(
                over_screen,
                ((self.board_surface.get_width() - over_screen.get_width()) /
                 2,
                 (self.board_surface.get_height() - over_screen.get_height()) /
                 6))

        if self.game_state.done:
            self.draw_over()
            self.play_state = False
            self.operate_play_buttons[0].set_text('开始游戏')

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
            self.black_player.play(self)
        elif self.play_state and self.game_state.turn() == go_engine.WHITE and \
                not isinstance(self.white_player, HumanPlayer):
            self.white_player.play(self)

        # 执行action
        if self.play_state and self.game_state.turn(
        ) == go_engine.BLACK and self.black_player.action is not None:
            self.play_step(self.black_player.action)
            self.black_player.action = None
            self.white_player.allow = True
        elif self.play_state and self.game_state.turn(
        ) == go_engine.WHITE and self.white_player.action is not None:
            self.play_step(self.white_player.action)
            self.white_player.action = None
            self.black_player.allow = True

        # 落子进度动画绘制
        if self.black_player.speed is not None:
            self.draw_speed(self.black_player.speed[0],
                            self.black_player.speed[1])
            self.black_player.speed = None
        elif self.white_player.speed is not None:
            self.draw_speed(self.white_player.speed[0],
                            self.white_player.speed[1])
            self.white_player.speed = None

    def event_control(self, event: pygame.event.Event):
        """
        游戏控制：根据pygame.event触发相应游戏状态

        1. 当Player为HumanPlayer时控制玩家落子
        2. 根据event对ct_manager进行更新

        :param event:
        :return:
        """
        # HumanPlayer落子
        next_player = self.next_player()
        if self.play_state and isinstance(next_player, HumanPlayer):
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and \
                    pos_in_surface(event.pos, self.board_surface):
                action = self.mouse_pos_to_action(event.pos)
                if self.game_state.action_valid(action):
                    if self.game_state.turn() == go_engine.BLACK:
                        self.black_player.action = action
                    else:
                        self.white_player.action = action
                else:
                    print('Invalid Action')
        # controls更新
        self.manager.control_update(event)

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

    def mouse_pos_to_action(self, mouse_pos):
        """将鼠标位置转换为action"""
        if 0 < mouse_pos[0] < SCREENHEIGHT and 0 < mouse_pos[1] < SCREENHEIGHT:
            # 将鼠标点击坐标转action，mouse_pos[0]对应列坐标，mouse_pos[1]对应行坐标
            row = round((mouse_pos[1] - SCREEN_SIZE * 20) / self.block_size)
            if row < 0:
                row = 0
            elif row > self.board_size - 1:
                row = self.board_size - 1
            col = round((mouse_pos[0] - SCREEN_SIZE * 20) / self.block_size)
            if col < 0:
                col = 0
            elif col > self.board_size - 1:
                col = self.board_size - 1
            return row * self.board_size + col

    @staticmethod
    def create_buttons(
        surface: pygame.Surface,
        button_texts: List[str],
        call_functions: List[Callable],
        first_pos: List[int or float],
        button_margin: Union[int, float],
        font_size: int = 14,
        size: Union[Tuple[int], List[int]] = (87, 27),
        text_color: Union[Tuple[int], List[int]] = (0, 0, 0),
        up_color: Union[Tuple[int], List[int]] = (225, 225, 225),
        down_color: Union[Tuple[int], List[int]] = (190, 190, 190),
        outer_edge_color: Union[Tuple[int], List[int]] = (240, 240, 240),
        inner_edge_color: Union[Tuple[int], List[int]] = (173, 173, 173)
    ) -> List[Button]:
        """
        批量地创建Button控件

        :param surface: Button绘制的surface
        :param button_texts: Button显示文本
        :param call_functions: Button的点击调用的函数
        :param first_pos: 第一个按钮绘制的位置
        :param button_margin: 相邻两个按钮之间的间隔
        :param font_size: 按钮字体大小
        :param size: 按钮大小
        :param text_color: 按钮文本颜色
        :param up_color: 按钮未被点击时颜色
        :param down_color: 按钮被点击时颜色
        :param outer_edge_color: 按钮外边框颜色
        :param inner_edge_color: 按钮内边框颜色
        :return: List[Button]
        """
        assert len(button_texts) == len(call_functions)

        buttons = []

        pos_next = copy.copy(first_pos)
        for btn_text, call_fct in zip(button_texts, call_functions):
            button = Button(surface,
                            btn_text,
                            pos_next,
                            call_fct,
                            size=size,
                            font_size=font_size,
                            text_color=text_color,
                            up_color=up_color,
                            down_color=down_color,
                            outer_edge_color=outer_edge_color,
                            inner_edge_color=inner_edge_color)
            buttons.append(button)
            pos_next[1] += button_margin
        return buttons

    @staticmethod
    def create_player(player_id: int) -> Player:
        """根据player_id创建player"""
        if player_id == 0:
            player = HumanPlayer()
        elif player_id == 1:
            player = RandomPlayer()
        elif player_id in [2, 3, 4, 5, 6,7, 8, 9, 10, 11]:
            player = MCTSPlayer_Alpha(n_playout=400 * (player_id - 1))
        # elif player_id in [2, 3, 4, 5, 6]:
        #     player = MCTSPlayer_Alpha(n_playout=400 * (player_id - 1))
        # elif player_id in [7, 8, 9, 10, 11]:
        #     player = MCTSPlayer_Mine(n_playout=400 * (player_id - 6))
        else:
            player = Player()
        return player

    def fct_for_black_player(self):
        # 切换玩家，会使游戏暂停
        self.play_state = False
        # 被切换掉的玩家对象失效
        self.black_player.valid = False
        self.operate_play_buttons[0].set_text('开始游戏')

        if self.game_state.turn() == go_engine.BLACK:
            if isinstance(self.black_player, MCTSPlayer_Alpha):
                self.draw_speed(0, 1)

        self.black_player_id += 1
        # player_num为游戏支持的Player总数
        player_num = 12
        self.black_player_id %= player_num

        # 将当前Player设置为响应Player
        self.black_player = self.create_player(self.black_player_id)
        self.pmc_buttons[0].set_text(self.black_player.name)

    def fct_for_white_player(self):
        # 切换玩家，会使游戏暂停
        self.play_state = False
        self.white_player.valid = False
        self.operate_play_buttons[0].set_text('开始游戏')

        if self.game_state.turn() == go_engine.WHITE:
            if isinstance(self.white_player, MCTSPlayer_Alpha):
                self.draw_speed(0, 1)

        self.white_player_id += 1
        # player_num为游戏支持的Player总数
        player_num = 12
        self.white_player_id %= player_num

        # 将当前Player设置为响应Player
        self.white_player = self.create_player(self.white_player_id)
        self.pmc_buttons[1].set_text(self.white_player.name)

    def fct_for_play_game(self):
        # 当开始游戏按钮被点击
        if self.play_state:

            # 游戏在进行状态时点击该按钮，游戏进入暂停状态
            self.operate_play_buttons[0].set_text('开始游戏')
            self.play_state = False
            # 切换至暂停状态，退出落子action计算循环
            self.next_player().valid = False
        else:
            # 游戏在未进行状态时点击该按钮
            if self.game_state.done:
                self.game_state.reset()
                self.draw_board()
                self.draw_pieces()
                self.black_player.allow = True
            else:
                self.draw_pieces()
                self.next_player().valid = True
            self.operate_play_buttons[0].set_text('暂停游戏')
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
                self.draw_board()
                self.draw_pieces()
                self.draw_mark(action)

            elif len(self.game_state.board_state_history) == 2:
                self.game_state.reset()
                self.draw_board()
                self.draw_pieces()

    def fct_for_restart(self):
        # 当重新开始按钮被点击
        self.play_state = True
        self.operate_play_buttons[0].set_text('暂停游戏')

        self.black_player.valid = False
        self.white_player.valid = False
        self.black_player = self.create_player(self.black_player_id)
        self.white_player = self.create_player(self.white_player_id)

        self.game_state.reset()
        self.draw_board()
        self.draw_pieces()

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


if __name__ == '__main__':
    # 功能测试
    game = GameEngine()
    while True:
        for evt in pygame.event.get():
            game.event_control(evt)
        game.take_action()
        pygame.display.update()

    # 算法效果测试第一步：修改mcts中的reward,修改下面的white/black player
    # game = GameEngine()
    
    # ntimes = 100
    
    # result = {'parameters':[],'id':[],'count':[],'topcount':[],'ranks':[],'actions':[],'time':[]}
    # startTime = time.time()
    # for id in range(4, 7):
    #     idStartTime = time.time()
    #     n = 0
    #     count = 0
    #     topcount = 0

    #     game.white_player = game.create_player(id) #
    #     game.pmc_buttons[1].set_text(game.white_player.name) #
    #     game.white_player_id = id
    #     result['id'].append(id)
    
    #     actionList =[]
    #     rankList = []
    #     # 设置实验次数
    #     while n < ntimes:
    
    #         n += 1
    #         game.fct_for_play_game()
    
    #         while True:
    #             for evt in pygame.event.get():
    #                 game.event_control(evt)

                
    #             game.take_action()
    #             pygame.display.update()
    #             if game.white_player.action != None: #
    #                 break

    #         if game.white_player.action == 9: #
    #             count += 1

    #         rank = game.white_player.rank #
    #         if rank <3:
    #             topcount += 1
    #         parameters = game.white_player.parameters
    #         rankList.append(rank) #

    #         row = game.white_player.action // game.board_size #
    #         column = game.white_player.action % game.board_size #
    #         position = (row,column)
    #         actionList.append(position)
    #         print('算法',id,'第',n,'轮',position)
    #         game.fct_for_restart()
    #         game.fct_for_play_game()
    
    #     result['parameters'].append(parameters)
    #     result['ranks'].append(rankList) #

    #     result['count'].append(count)
    #     result['topcount'].append(topcount)
    #     result['actions'].append(actionList)
    #     timeSpent = round((time.time() - idStartTime) / ntimes,2)
    #     result['time'].append(timeSpent)

    #     print('Stats:',id,count,topcount,actionList,timeSpent)
        
    
    # print('Time:', round(time.time() - startTime,2))
    # print('Final Result:',result)
    # df = pd.DataFrame(result)
    # df.to_csv('result.csv',mode='a', index=False)
    # game.fct_for_exit()
