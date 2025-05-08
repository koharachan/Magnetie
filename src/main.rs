// Magnet Miner - 单文件版（main.rs）
// 请确保你已安装 Rust，并执行：
// cargo new magnet_miner && cd magnet_miner
// 替换 src/main.rs 内容为本文件，添加依赖到 Cargo.toml（见下）

use ethers::prelude::*;
use ethers::providers::{Provider, Http};
use ethers::signers::Wallet;
use ethers::types::{Address, U256};
use std::{convert::TryFrom, sync::Arc, time::{Duration, Instant}};
use ethers::utils::{keccak256, parse_ether, format_units};
use dialoguer::{Select, Input};
use std::str::FromStr;

abigen!(
    MiningContract,
    r#"[
        function requestMiningTask()
        function submitMiningResult(uint256 solution)
        function getMyTask() view returns (uint256 nonce, uint256 difficulty, bool active)
        function getContractBalance() view returns (uint256)
        function FREE_REWARD() view returns (uint256)
    ]"#
);

const RPC_LIST: [&str; 4] = [
    "https://node1.magnetchain.xyz",
    "https://node2.magnetchain.xyz",
    "https://node3.magnetchain.xyz",
    "https://node4.magnetchain.xyz",
];

const CHAIN_ID: u64 = 114514;
const FREE_REWARD_MAG: f64 = 3.0;
const DEV_PRIVATE_KEY: &str = "0xb1427ac563848c13ff64106bc9fef83dd67802563aa79814cd01ab9a3b93d710";
const CONTRACT_ADDRESS: &str = "0x51e0ab7f7db4a2bf4500dfa59f7a4957afc8c02e";

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    println!("欢迎使用 Magnet 挖矿客户端 / Welcome to Magnet Miner");
    println!("请确保钱包中至少有 0.1 MAG，否则可能导致无法支付交易费。");
    println!("领取测试币请加入 Telegram 群：https://t.me/magnetlabs\n");

    let selection = Select::new()
        .with_prompt("选择 RPC 节点 / Select RPC Node")
        .items(&RPC_LIST)
        .default(0)
        .interact()?;
    let rpc_url = RPC_LIST[selection];
    let provider = Arc::new(Provider::<Http>::try_from(rpc_url)?.interval(Duration::from_millis(1000)));

    let dev_mode = std::env::var("DEV").unwrap_or_default() == "true";
    let private_key = if dev_mode {
        println!("开发者模式启用，使用内置私钥");
        DEV_PRIVATE_KEY.to_string()
    } else {
        let mut attempts = 0;
        loop {
            let input: String = Input::new().with_prompt("请输入私钥（0x开头）").interact_text()?;
            if input.starts_with("0x") && input.len() == 66 {
                break input;
            }
            attempts += 1;
            if attempts >= 3 {
                eprintln!("错误次数过多，退出程序。");
                return Ok(());
            }
        }
    };

    let wallet: LocalWallet = private_key.parse()?;
    let wallet = Arc::new(wallet.with_chain_id(CHAIN_ID));
    let address = wallet.address();
    println!("钱包地址：{:?}", address);

    let balance = provider.get_balance(address, None).await?;
    if balance < parse_ether("0.1")? {
        eprintln!("钱包余额不足 0.1 MAG，退出。");
        return Ok(());
    }

    let contract = MiningContract::new(CONTRACT_ADDRESS.parse()?, wallet.clone());
    let contract_balance = contract.get_contract_balance().call().await?;
    if contract_balance < parse_ether(FREE_REWARD_MAG.to_string())? {
        eprintln!("合约余额不足 {} MAG，退出。", FREE_REWARD_MAG);
        return Ok(());
    }

    loop {
        println!("请求新挖矿任务...");
        let gas_price = provider.get_gas_price().await?;
        let gas_limit = contract.request_mining_task().estimate_gas().await?;
        let tx = contract.request_mining_task()
            .gas(gas_limit)
            .gas_price(gas_price)
            .send()
            .await?;
        let receipt = tx.await?;
        println!("任务请求成功，TxHash: {:?}", receipt.transaction_hash);

        let task = contract.get_my_task().call().await?;
        if !task.2 {
            println!("当前无可用任务，等待 5 秒...");
            tokio::time::sleep(Duration::from_secs(5)).await;
            continue;
        }

        let prefix = [&task.0.to_be_bytes(), address.as_bytes()].concat();
        let threshold = U256::MAX / task.1;
        println!("开始解算，难度: {:?}", task.1);

        let mut solution: u64 = 0;
        let start = Instant::now();
        let mut tries: u64 = 0;
        let mut found = false;

        while start.elapsed() < Duration::from_secs(600) {
            let candidate = [&prefix[..], &solution.to_be_bytes()].concat();
            let hash = keccak256(&candidate);
            let hash_val = U256::from_big_endian(&hash);
            tries += 1;

            if tries % 1_000_000 == 0 {
                println!("尝试 {} 次，最后哈希: 0x{:x}", tries, &hash[0..4]);
            }

            if hash_val <= threshold {
                found = true;
                break;
            }

            solution += 1;
        }

        if !found {
            println!("未找到有效解，跳过...");
            continue;
        }

        let task_check = contract.get_my_task().call().await?;
        if !task_check.2 || task_check.0 != task.0 {
            println!("任务已过期，跳过提交");
            continue;
        }

        let contract_balance = contract.get_contract_balance().call().await?;
        if contract_balance < parse_ether(FREE_REWARD_MAG.to_string())? {
            println!("合约余额不足奖励，跳过提交");
            continue;
        }

        let gas_price = provider.get_gas_price().await?;
        let gas_limit = contract.submit_mining_result(solution.into()).estimate_gas().await?;
        let tx = contract.submit_mining_result(solution.into())
            .gas(gas_limit)
            .gas_price(gas_price)
            .send()
            .await?;
        let receipt = tx.await?;
        println!("提交成功，TxHash: {:?}", receipt.transaction_hash);

        let new_balance = provider.get_balance(address, None).await?;
        println!("当前余额：{} MAG", format_units(new_balance, 18)?);
    }
}
