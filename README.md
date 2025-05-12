# Magnetie

## 关于这个项目
本项目使用 XYACE 协议开源。

## 使用指南

### 1. 环境配置
1. 激活虚拟环境（推荐 Python 3.12）
   ```bash
   # Windows
   .venv\Scripts\activate
   
   # Linux/macOS
   source .venv/bin/activate
   ```

2. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

### 2. 配置说明
在项目根目录创建 `.env` 文件（根目录有个.env.example，可以cp之后来改），配置以下参数：

| 参数 | 说明 | 示例 |
|------|------|------|
| PRIVATE_KEY | 钱包私钥 | `PRIVATE_KEY=0x你的钱包私钥` |
| RPC_URL | 节点地址 | 默认即可，或参考 [节点信息](https://github.com/MagnetPOW/Node-Information) |
| MINER_WORKERS | 挖矿线程数 | 根据机器配置设置 |
| MIN_CONTRACT_BALANCE | 最低合约余额 | 低于此值停止挖矿 |
| DEV_MODE | 开发者模式 | 用于调试，默认关闭 |

### 3. 运行程序
```bash
python -m src.cli
```
或
```bash
python src/cli.py
```

## 开发者说明
- dev模式可帮助开发者在移植到其他平台时方便调试
- 详细API文档请参考 `docs` 目录
