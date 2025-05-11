import os
import time
from typing import Optional, Tuple
from web3.exceptions import TransactionNotFound
from src.logging_config import setup_logger
from src.utils.hashing import MiningSession
from .blockchain import BlockchainClient

logger = setup_logger(__name__)

MIN_WALLET_BALANCE = float(os.getenv("MIN_BALANCE", 0.1))
MIN_CONTRACT_BALANCE = float(os.getenv("MIN_CONTRACT_BALANCE", 0.3))

current_task: Optional[Tuple[int, int]] = None  # (nonce, difficulty)

# 新增全局变量保存最近一次挖矿会话
_last_mining_session: Optional[MiningSession] = None


def check_balances(client: BlockchainClient) -> bool:
    try:
        wallet_balance = client.get_balance()
        contract_balance = client.get_contract_balance()

        if wallet_balance < MIN_WALLET_BALANCE:
            logger.error("钱包余额不足，你干嘛去了？")
            return False

        if contract_balance < MIN_CONTRACT_BALANCE:
            logger.error(f"合约余额不足，就 ({MIN_CONTRACT_BALANCE} MAG) 了，ta们是不是跑路了？")
            return False

        return True
    except Exception as e:
        logger.exception("余额检查失败")  # 已使用 e，无需修改
        return False


def request_task_with_retry(client: BlockchainClient, max_retries: int = 5) -> Optional[Tuple[int, int]]:
    for attempt in range(max_retries):
        try:
            tx_hash = client.request_mining_task()
            logger.info(f"[TX] 任务请求交易: {tx_hash}")

            if not client.wait_for_transaction(tx_hash):
                logger.warning("交易未被确认，尝试重新获取...")
                continue

            task_data = client.get_mining_task()
            logger.debug(f"[DEBUG] 合约返回数据: {task_data}")

            if not task_data or not isinstance(task_data, tuple) or len(task_data) < 3:
                logger.warning("无效任务数据，尝试重新获取...")
                time.sleep(2 ** attempt)
                continue

            nonce, difficulty, active = task_data

            if active:
                logger.info(f"获取新任务: Nonce={nonce}, Difficulty={difficulty}")
                return nonce, difficulty

            logger.warning(f"任务未激活，尝试 {attempt + 1}/{max_retries}...")

        except TransactionNotFound:
            logger.warning("交易未被网络确认，尝试重新获取...")
            time.sleep(2 ** attempt)
        except Exception as e:
            logger.error(f"请求任务失败: {str(e)}")
            time.sleep(2 ** attempt)

    return None


def mine_current_task(client: BlockchainClient) -> Optional[int]:
    global _last_mining_session
    if not current_task:
        logger.error("未找到任务")
        return None

    nonce, difficulty = current_task
    logger.info(f"开始挖矿 Nonce: {nonce} | 难度: {difficulty}")

    session = MiningSession(nonce, client.account.address, difficulty)
    _last_mining_session = session  # 保存当前会话
    solution, raw_hashrate = session.find_solution(0, 2 ** 64)

    if solution is None:
        logger.warning("未找到有效方案")
    return solution


def get_current_hashrate() -> float:
    """获取最近一次挖矿会话的算力（H/s），无则返回0"""
    if _last_mining_session is not None:
        current_time = time.time()
        elapsed = current_time - _last_mining_session.start_time
        total_count = next(_last_mining_session.global_counter) - 1
        hashrate = total_count / max(elapsed, 1e-9)
        return hashrate
    return 0.0


def submit_solution(client: BlockchainClient, solution: int) -> bool:
    logger.info(f"提交方案: {solution:#x}")

    try:
        tx_hash = client.submit_solution(solution)
        logger.info(f"[TX] 提交交易: {tx_hash}")

        if client.wait_for_transaction(tx_hash):
            logger.info("提交成功！")
            return True
        else:
            logger.error("交易未被确认")
            return False

    except Exception as e:
        logger.error(f"提交失败: {str(e)}")
        return False


def run_mining_process(client: BlockchainClient):
    global current_task

    logger.info("======= 小原酱世界第一可爱 =======")

    while True:
        try:
            if not check_balances(client):
                logger.warning("余额不足，等待5秒后重试...")
                time.sleep(5)
                continue

            task = request_task_with_retry(client)
            if task is None:
                logger.warning("无法获取任务，等待5秒后重试...")
                time.sleep(5)
                continue

            current_task = task

            solution = mine_current_task(client)
            if solution is None:
                logger.warning("本轮挖矿无结果，重新开始...")
                continue

            if submit_solution(client, solution):
                current_task = None

        except Exception as e:
            logger.critical(f"炸了: {str(e)}", exc_info=True)
            logger.info("5秒后自动重启...")
            time.sleep(5)
