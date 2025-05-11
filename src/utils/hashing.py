from eth_hash.auto import keccak
import time
from typing import Optional, Tuple
import struct
from concurrent.futures import ThreadPoolExecutor
import sys
import threading
import itertools
import os


class MiningSession:
    def __init__(self, nonce: str, address: str, difficulty: int):
        # 预处理固定前缀
        self.nonce = bytes.fromhex(nonce[2:])  # 转换为32字节
        self.address = bytes.fromhex(address[2:])  # 转换为20字节
        self.difficulty = difficulty
        self.target = (2 ** 256) // difficulty

        # 预计算固定前缀
        self.prefix = struct.pack('=32s20s', self.nonce, self.address)

        # 初始化计数器
        self.start_time = time.time()
        self.global_counter = itertools.count()
        self.hashrate = 0

        # 进度显示锁
        self.lock = threading.Lock()

    def _calculate_chunk(self, start: int, chunk_size: int) -> Optional[int]:
        """计算一个区块范围内的哈希"""
        for solution in range(start, start + chunk_size):
            data = self.prefix + solution.to_bytes(32, 'big', signed=False)
            hash_int = int.from_bytes(keccak(data), 'big')
            
            # 更新计数器
            next(self.global_counter)
            
            if hash_int < self.target:
                return solution
        return None

    def _show_progress(self):
        """异步实时算力显示"""
        with self.lock:
            current_time = time.time()
            elapsed = current_time - self.start_time
            total_count = next(self.global_counter) - 1  # 获取当前计数
            hashrate = total_count / max(elapsed, 1e-9)
            sys.stdout.write(f"\r当前算力: {hashrate:,.0f} H/s | 尝试数: {total_count:,}")
            sys.stdout.flush()

    def find_solution(self, start: int, end: int) -> Optional[Tuple[int, float]]:
        """带统计的解决方案搜索"""
        print(f"开始搜索范围 {start}-{end}")
        
        # 优化区块大小：每个区块1000个数字
        CHUNK_SIZE = 1000
        cpu_count = os.cpu_count() or 1
        
        # 停止标志
        solution_found = threading.Event()
        
        def process_chunk(chunk_start: int) -> Optional[int]:
            if solution_found.is_set():
                return None
            result = self._calculate_chunk(chunk_start, CHUNK_SIZE)
            if result is not None:
                solution_found.set()
            return result

        # 异步监控进度
        def progress_monitor():
            while not solution_found.is_set():
                self._show_progress()
                time.sleep(1)

        # 启动进度监控线程
        monitor = threading.Thread(target=progress_monitor, daemon=True)
        monitor.start()

        try:
            with ThreadPoolExecutor(max_workers=cpu_count) as executor:
                current = start
                while current < end and not solution_found.is_set():
                    # 提交一批任务
                    chunk_starts = range(current, min(current + CHUNK_SIZE * cpu_count * 10, end), CHUNK_SIZE)
                    futures = [executor.submit(process_chunk, chunk_start) for chunk_start in chunk_starts]
                    
                    # 等待这一批任务完成
                    for future in futures:
                        result = future.result()
                        if result is not None:
                            elapsed = time.time() - self.start_time
                            hashrate = next(self.global_counter) / max(elapsed, 1e-9)
                            print(f"\n找到有效解: {hex(result)}")
                            solution_found.set()
                            return result, hashrate
                    
                    current += CHUNK_SIZE * cpu_count * 10
                    
        finally:
            solution_found.set()
            monitor.join(timeout=0.1)

        return None
