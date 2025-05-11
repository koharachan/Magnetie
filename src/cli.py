import os
import signal
import sys
import threading
import time  # 新增
import keyboard  # 用于监听键盘事件
from dotenv import load_dotenv
from src.core.blockchain import BlockchainClient
from src.core.miner import run_mining_process
from src.core.miner import get_current_hashrate  # 新增导入
from src.logging_config import setup_logger ,logging
logger = setup_logger(__name__)

# 挖矿程序状态
mining_running = False

def handle_exit_signal(signum, frame):
    """捕获 Ctrl+C 信号退出程序"""
    print("\n程序退出中...")
    global mining_running
    mining_running = False
    sys.exit(0)

def start_mining_process(client):
    """启动挖矿进程"""
    global mining_running
    global mining_hashrate
    mining_running = True
    coordinator = run_mining_process(client)
    while mining_running:
        # 假设`run_mining_process`会返回实时的算力值
        mining_hashrate = coordinator.get_current_hashrate()
        # 持续运行矿工
        coordinator.run()

def main():
    # 加载环境变量
    load_dotenv()

    # 验证配置
    required_vars = ['PRIVATE_KEY', 'RPC_URL']
    if not all(os.getenv(var) for var in required_vars):
        logging.error("缺少必需的环境变量配置！请检查.env文件")
        return

    try:
        # 初始化区块链客户端
        client = BlockchainClient(
            rpc_url=os.getenv('RPC_URL'),
            private_key=os.getenv('PRIVATE_KEY')
        )

        # 注册信号处理函数，捕获 Ctrl+C 信号
        signal.signal(signal.SIGINT, handle_exit_signal)

        # 启动挖矿线程
        mining_thread = threading.Thread(target=start_mining_process, args=(client,))
        mining_thread.daemon = True
        mining_thread.start()

        logging.info("====== 挖矿程序已启动 ======")
        logging.info(f"钱包地址: {client.account.address}")


        # 实时监听按键
        while True:
            if keyboard.is_pressed('h'):  # 按 'h' 显示算力
                print(f"当前算力: {get_current_hashrate():,.0f} H/s")
                time.sleep(0.5)  # 防止重复触发
            if keyboard.is_pressed('esc'):    # 按 'esc' 退出程序
                print("\n程序退出中...")
                break

    except Exception as e:
        logging.error(f"程序运行异常: {str(e)}", exc_info=True)


if __name__ == "__main__":
    main()
