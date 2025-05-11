from web3 import Web3

# 填写你的真实ABI
YOUR_ABI = [
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

try:
    w3 = Web3()
    w3.eth.contract(abi=YOUR_ABI)
    print("✅ ABI验证通过")
except ValueError as e:
    print(f"❌ ABI格式错误: {str(e)}")