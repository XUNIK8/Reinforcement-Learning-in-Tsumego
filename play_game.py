
from game_engine import GameEngine
import pygame
import sys


if __name__ == '__main__':
    game = GameEngine()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:  # 退出事件
                sys.exit()
            else:
                game.event_control(event)
        # 落子
        game.take_action()
        # 屏幕刷新
        pygame.display.update()
