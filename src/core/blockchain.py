import os
import time
import logging
from web3 import Web3
from web3.contract import Contract
from web3.types import Wei
from typing import Optional, Tuple
from src.logging_config import setup_logger
logger = setup_logger(__name__)

# 配置日志
LOG_LEVEL = logging.DEBUG if os.getenv("DEV") == "true" else logging.INFO

# 合约地址（必须使用校验和格式）
CONTRACT_ADDRESS = Web3.to_checksum_address('0x51e0ab7f7db4a2bf4500dfa59f7a4957afc8c02e')

# 合约ABI
CONTRACT_ABI = [
    {
        "inputs": [],
        "stateMutability": "nonpayable",
        "type": "constructor"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "reward", "type": "uint256"}
        ],
        "name": "MiningReward",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "difficulty", "type": "uint256"}
        ],
        "name": "NewMiningTask",
        "type": "event"
    },
    {
        "inputs": [],
        "name": "requestMiningTask",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "solution", "type": "uint256"}],
        "name": "submitMiningResult",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getMyTask",
        "outputs": [
            {"internalType": "uint256", "name": "nonce", "type": "uint256"},
            {"internalType": "uint256", "name": "difficulty", "type": "uint256"},
            {"internalType": "bool", "name": "active", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getContractBalance",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]


class BlockchainClient:
    def __init__(self, rpc_url: str, private_key: str):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 30}))
        if not self.w3.is_connected():
            raise ConnectionError("无法连接至RPC节点")

        self.account = self._validate_account(private_key)
        self.contract = self._load_contract()
        logger.info(f"[初始化] 区块链客户端初始化成功，地址: {self.account.address}")

    def _validate_account(self, private_key: str):
        """验证私钥有效性"""
        try:
            account = self.w3.eth.account.from_key(private_key)
            if not Web3.is_checksum_address(account.address):
                raise ValueError("地址校验失败")
            return account
        except ValueError as ve:
            logger.error(f"[错误] 无效的私钥: {str(ve)}")
            raise

    def _load_contract(self) -> Contract:
        """加载智能合约并验证地址"""
        try:
            if not Web3.is_checksum_address(CONTRACT_ADDRESS):
                raise ValueError("合约地址校验失败")

            contract = self.w3.eth.contract(
                address=CONTRACT_ADDRESS,
                abi=CONTRACT_ABI
            )

            if not contract.all_functions():
                raise ValueError("合约ABI无效")

            logger.debug(f"[调试] 合约加载成功: {contract.address}")
            return contract
        except Exception as e:
            logger.error(f"[错误] 合约加载失败: {str(e)}")
            raise

    def request_mining_task(self) -> Optional[str]:
        """请求新挖矿任务并返回交易哈希"""
        try:
            gas_estimate = self.contract.functions.requestMiningTask().estimate_gas({
                'from': self.account.address
            })
            logger.debug(f"[调试] Gas估算: {gas_estimate} gas")

            tx = self.contract.functions.requestMiningTask().build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': Wei(gas_estimate * 2),
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.w3.eth.chain_id
            })

            logger.debug(f"[调试] 交易构建完成: {tx}")

            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            logger.info(f"[任务请求] 任务请求已发送 TX: {tx_hash.hex()}")
            return tx_hash.hex()
        except Exception as e:
            logger.error(f"[错误] 任务请求失败: {str(e)}")
            return None

    def get_mining_task(self, retries: int = 3) -> Optional[Tuple[str, int, bool]]:
        """
        获取当前挖矿任务（带重试机制），使用 web3.to_hex() 处理大整数 nonce

        Returns:
            Optional[Tuple[str, int, bool]]: (nonce_hex, difficulty, active)
        """
        for attempt in range(retries):
            try:
                # 调用合约获取任务（强制指定调用者地址）
                result = self.contract.functions.getMyTask().call({
                    'from': self.account.address
                })

                # 打印原始返回值（调试用）
                logger.debug(f"[调试] 原始合约返回值: {result}, 类型: {type(result)}")

                # 强制转换为元组（兼容 list 类型返回）
                if isinstance(result, list) and len(result) == 3:
                    result = tuple(result)
                elif not isinstance(result, tuple) or len(result) != 3:
                    raise ValueError("合约返回数据格式异常")

                # 检查是否为空任务
                if result[0] == 0 and result[1] == 0 and not result[2]:
                    logger.warning(f"[警告] 合约返回空任务，等待重试... 尝试次数: {attempt + 1}/{retries}")
                    time.sleep(2 ** attempt)
                    continue

                # 转换为十六进制字符串 + 显式类型转换
                nonce_hex = Web3.to_hex(result[0])  # 使用 web3.to_hex() 处理大整数
                difficulty = int(result[1])
                active = bool(result[2])

                logger.info(f"[获取任务] 成功获取任务: Nonce={nonce_hex}, Difficulty={difficulty}, Active={active}")
                return (nonce_hex, difficulty, active)

            except ValueError as ve:
                logger.error(f"[错误] 数据解析失败: {str(ve)}")
                if attempt == retries - 1:
                    return None
                time.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"[错误] 获取任务失败: {str(e)}")
                return None

        logger.error("[错误] 最大重试次数已用完，任务获取失败")
        return None

    def submit_solution(self, solution: int) -> Optional[str]:
        """提交解决方案"""
        try:
            # 预检查任务状态
            task = self.get_mining_task()
            if not task or not task[2]:
                raise ValueError("无有效任务可提交")

            logger.info(f"[提交] 解决方案: {solution}, 当前任务: {task}")

            # 构建交易
            tx = self.contract.functions.submitMiningResult(solution).build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.w3.eth.chain_id
            })

            # 动态估算Gas
            try:
                tx['gas'] = self.contract.functions.submitMiningResult(solution).estimate_gas({
                    'from': self.account.address
                }) * 2
            except Exception as e:
                logger.warning(f"[警告] Gas估算失败，使用默认值: {str(e)}")
                tx['gas'] = 300000

            logger.debug(f"[调试] 提交交易构建完成: {tx}")

            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            logger.info(f"[提交] 解决方案已提交 TX: {tx_hash.hex()}")
            return tx_hash.hex()
        except Exception as e:
            logger.error(f"[错误] 提交失败: {str(e)}")
            return None

    def get_balance(self) -> float:
        """获取钱包余额（单位：MAG）"""
        try:
            balance_wei = self.w3.eth.get_balance(self.account.address)
            balance_mag = self.w3.from_wei(balance_wei, 'ether')
            return balance_mag
        except Exception as e:
            logger.error(f"[错误] 余额查询失败: {str(e)}")
            return 0.0

    def get_contract_balance(self) -> float:
        """获取合约池余额（单位：MAG）"""
        try:
            balance_wei = self.contract.functions.getContractBalance().call()
            balance_mag = self.w3.from_wei(balance_wei, 'ether')
            return balance_mag
        except Exception as e:
            logger.error(f"[错误] 合约余额查询失败: {str(e)}")
            return 0.0

    def wait_for_transaction(self, tx_hash: str, timeout=120) -> bool:
        """等待交易确认"""
        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
            logger.debug(f"[调试] 交易收据: {receipt}")

            if receipt.status == 1:
                logger.info(f"[交易确认] 交易已确认 Block: {receipt.blockNumber}")
                return True
            logger.error(f"[交易失败] 交易失败: {receipt.transactionHash.hex()}")
            return False
        except Exception as e:
            logger.error(f"[错误] 等待交易超时: {str(e)}")
            return False