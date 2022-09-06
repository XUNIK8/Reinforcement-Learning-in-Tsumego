# Reinforcement-Learning-in-Tsumego
## 介绍(Introduction)
- Tsumego是在开源项目CleverGo基础上改进的一款专适用于围棋死活问题求解的智能围棋博弈系统，核心是强化学习算法（蒙特卡洛树搜索和UCT）。
- 可视化界面和围棋规则编码主要参考了GymGo&CleverGo，并在其基础上对代码逻辑进行了简化。但原项目基于的是正常围棋博弈的玩法规则，而非死活题。因此本项目额外增加了一些围棋死活问题下的规则函数，如死棋/活棋判定、游戏终局判定、死活题输赢判定、真假眼判定等等，从而更适应围棋死活题的场景。
- 此项目的核心算法是强化学习——基于蒙特卡洛树搜索地UCT算法，参考了AlphoGo的算法原理实现了基本的MCTS算法和UCT算法，同时也创造性地对算法框架、回报函数、超参数等进行了改进，从而更适用于围棋死活题求解。
- 围棋规则、围棋死活题介绍、算法实现以及优化、围棋棋盘编码、参数组合优化 等内容可参考paper文件夹中的pdf文件。
- 欢迎交流，微信：XHJ20815

- Tsumego is an intelligent Go game system for solving dead-end Go problems, based on the open source project CleverGo, with core reinforcement learning algorithms (Monte Carlo tree search and UCT).
- The visualization interface and Go rules coding are mainly based on GymGo & CleverGo, and the code logic has been simplified on top of them. However, the original project is based on the rules of normal Go game play, not on dead or alive questions. Therefore, this project adds some additional rule functions for dead/alive Go problems, such as dead/alive game decision, game endgame decision, dead/alive problem win/lose decision, true/false eye decision, etc., so as to better fit the scenario of dead/alive Go problems.
- The core algorithm of this project is reinforcement learning - UCT algorithm based on Monte Carlo tree search. The basic MCTS algorithm and UCT algorithm are implemented with reference to AlphoGo's algorithm principle, and the algorithm framework, payoff function, hyperparameters, etc. are also creatively improved to be more suitable for solving dead-end Go problems. The algorithm framework, payoff function, hyperparameters, etc. are also creatively improved to be more suitable for solving dead-end Go problems.
- The rules of Go, the introduction of Go dead-end problems, algorithm implementation and optimization, Go board coding, parameter combination optimization, etc. can be found in the pdf file in the paper folder.
- Welcome to exchange, WeChat: XHJ20815

参考项目(Reference):
https://github.com/QPT-Family/QPT-CleverGo

### 项目文件说明(Project Document Description)
#### assets
- 包含了可视化围棋博弈系统所需的音频、图标、字体等，可选择性使用或替换。
- Includes audio, icons, fonts, etc. required for the visual Go gaming system, which can be optionally used or replaced
#### dataset
- 包含几个围棋死活题模板，将死活题转换为算法的输入矩阵，并在go_engine.py中调用。
- Contains several Go dead-end question templates, converts the dead-end questions into input matrices for the algorithm, and calls them in go_engine.py
#### GymGo
- 包含围棋博弈系统和围棋规则底层逻辑代码。
- Contains several Go dead-end question templates, converts the dead-end questions into input matrices for the algorithm, and calls them in go_engine.py
#### papaer
- 包含论文以及所用图例。
- Includes paper and graphs used
#### game_engine.py
- 围棋博弈系统实现的主要代码，Tsumego的主干部分，基于Pygame实现棋盘的可视化、人机交互、游戏控制函数等。
- The main code for the implementation of the Go gaming system, the main part of Tsumego, the visualization of the board based on Pygame, human-computer interaction, game control functions, etc.
#### game_engine_linux.py
- 与game_engine.py基本一致，将主函数改为了循环嵌套从而搜索最优参数组合，用于在云服务器上自动运行，打印所有参数组合的效果。
- Basically the same as game_engine.py, the main function is nested in a loop to search for the best combination of parameters, and is used to run automatically on the cloud server to print the effect of all parameter combinations
#### go_engine.py
- 在GymGo基础上的围棋规则逻辑的编码实现，包含对棋盘的定义、落子逻辑实现、有效位置的判断、游戏终局的判断、输赢判断等。
- Coding implementation of Go rules logic based on GymGo, including definition of the board, implementation of drop logic, judgement of valid positions, judgement of the endgame, judgement of winning and losing, etc.
#### mcts_alpha.py
- 基于AlphaGo原理实现的MCTS算法（简化版），采用了UCT算法。
- MCTS algorithm (simplified version) implemented based on the AlphaGo principle, using the UCT algorithm
#### mcts_mine.py
- 自己实现的普通mcts算法，区别在于 在MCTS的selection阶段用随机选取代替了UCB方法。
- The difference is that the UCB method is replaced by random selection in the selection phase of MCTS.
#### player.py
- 对智能体玩家的类定义，可在此文件中更改调用的库从而更改使用的算法（mcts_alpha/mcts_mine）。
- For the class definition of the smart player, the library to be called can be changed in this file to change the algorithm used (mcts_alpha/mcts_mine)
#### play_game.py
- 程序启动入口，相当于主函数，调用game_engine.py。
- The program startup entry, equivalent to the main function, calls game_engine.py

### 主要功能介绍(Main Functions)
1. 运行play_game.py，出现可视化界面，点击开始游戏即自动显示dataset中调用的goMap死活题棋盘
- Run play_game.py, the visualization interface appears, click start the game that automatically displays the goMap dead or alive board called in the dataset.
![image](https://user-images.githubusercontent.com/56428735/188537090-40338ca0-3c1c-442c-bacd-9b8c918d5c4e.png)
2. 右上方可选择玩家，当为人类玩家时，即玩家鼠标手动点击棋盘落子点进行落子，当为MCTS算法时，则为强化学习智能体控制落子。
- The player can be selected at the top right, when it is a human player, i.e. the player clicks the board drop point manually to drop the pieces, when it is MCTS algorithm, it is a reinforcement learning intelligence controlling the drop.
3. 双方交替落子，直至该死活题分出胜负（黑胜/白胜）
- Both players alternate until the dead-end question is decided (black wins/white wins)
![image](https://user-images.githubusercontent.com/56428735/188537784-3ca08708-b094-4431-a02c-bc04ed2b54fb.png)
