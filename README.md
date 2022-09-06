# Reinforcement-Learning-in-Tsumego
- Tsumego是在开源项目CleverGo基础上改进的一款专适用于围棋死活问题求解的智能围棋博弈系统，核心是强化学习算法（蒙特卡洛树搜索和UCT）。
- 可视化界面和围棋规则编码主要参考了GymGo&CleverGo，并在其基础上对代码逻辑进行了简化。但原项目基于的是正常围棋博弈的玩法规则，而非死活题。因此本项目额外增加了一些围棋死活问题下的规则函数，如死棋/活棋判定、游戏终局判定、死活题输赢判定、真假眼判定等等，从而更适应围棋死活题的场景。
- 此项目的核心算法是强化学习——基于蒙特卡洛树搜索地UCT算法，参考了AlphoGo的算法原理实现了基本的MCTS算法和UCT算法，同时也创造性地对算法框架、回报函数、超参数等进行了改进，从而更适用于围棋死活题求解。
- 围棋规则、围棋死活题介绍、算法实现以及优化、围棋棋盘编码、参数组合优化 等内容可参考paper文件夹中的pdf文件。
- 欢迎交流，微信：XHJ20815

参考项目(Reference):
https://github.com/QPT-Family/QPT-CleverGo

### 项目文件说明
#### assets
包含了可视化围棋博弈系统所需的音频、图标、字体等，可选择性使用或替换。

#### dataset
包含几个围棋死活题模板，将死活题转换为算法的输入矩阵，并在go_engine.py中调用。

#### GymGo
包含围棋博弈系统和围棋规则底层逻辑代码。

#### papaer
包含论文以及所用图例。

#### game_engine.py
围棋博弈系统实现的主要代码，Tsumego的主干部分，基于Pygame实现棋盘的可视化、人机交互、游戏控制函数等。

#### game_engine_linux.py
与game_engine.py基本一致，将主函数改为了循环嵌套从而搜索最优参数组合，用于在云服务器上自动运行，打印所有参数组合的效果。

#### go_engine.py
在GymGo基础上的围棋规则逻辑的编码实现，包含对棋盘的定义、落子逻辑实现、有效位置的判断、游戏终局的判断、输赢判断等。

#### mcts_alpha.py
基于AlphaGo原理实现的MCTS算法（简化版），采用了UCT算法。

#### mcts_mine.py
自己实现的普通mcts算法，区别在于 在MCTS的selection阶段用随机选取代替了UCB方法。

#### player.py
对智能体玩家的类定义，可在此文件中更改调用的库从而更改使用的算法（mcts_alpha/mcts_mine）。

#### play_game.py
程序启动入口，相当于主函数，调用game_engine.py。

### 主要功能介绍
1. 运行play_game.py，出现可视化界面，点击开始游戏即自动显示dataset中调用的goMap死活题棋盘
![image](https://user-images.githubusercontent.com/56428735/188537090-40338ca0-3c1c-442c-bacd-9b8c918d5c4e.png)
2. 右上方可选择玩家，当为人类玩家时，即玩家鼠标手动点击棋盘落子点进行落子，当为MCTS算法时，则为强化学习智能体控制落子。
3. 双方交替落子，直至该死活题分出胜负（黑胜/白胜）
![image](https://user-images.githubusercontent.com/56428735/188537784-3ca08708-b094-4431-a02c-bc04ed2b54fb.png)
