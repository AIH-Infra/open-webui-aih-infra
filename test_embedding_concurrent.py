import asyncio
import time
import httpx
import tiktoken
import json
import sys

# 配置
API_URL = "http://106.15.124.238:18000/v1/embeddings"
MODEL_NAME = "text-embedding-bge-m3"
TOTAL_TASKS = 100
TARGET_TOKENS = 2048

def generate_text(token_count):
    # 使用 cl100k_base 编码（常用与 GPT-4/bge 等）
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
    except Exception:
        encoding = tiktoken.get_encoding("gpt2")
        
    base_text = "Testing connectivity and speed for embedding model. This is a concurrent benchmark test. "
    text = base_text
    while len(encoding.encode(text)) < token_count:
        text += base_text
    
    tokens = encoding.encode(text)[:token_count]
    return encoding.decode(tokens)

async def send_embedding_request(client, task_id, payload, headers):
    start_time = time.perf_counter()
    try:
        # 设置较长的超时时间，因为 100 个并发请求可能会导致排队
        response = await client.post(API_URL, json=payload, headers=headers, timeout=300.0)
        response.raise_for_status()
        end_time = time.perf_counter()
        latency = (end_time - start_time) * 1000
        print(f"任务 {task_id:3d}: 成功 - 耗时 {latency:8.2f} ms")
        return latency
    except Exception as e:
        end_time = time.perf_counter()
        print(f"任务 {task_id:3d}: 失败 - 耗时 {(end_time - start_time)*1000:8.2f} ms - 错误: {str(e)}")
        return None

async def run_concurrent_test():
    print(f"正在准备测试文本 ({TARGET_TOKENS} tokens)...")
    test_text = generate_text(TARGET_TOKENS)
    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL_NAME,
        "input": test_text
    }
    
    print(f"开始并发测试: 同时发起 {TOTAL_TASKS} 个请求对模型 {MODEL_NAME}")
    print(f"API 地址: {API_URL}")
    print("-" * 70)
    
    start_total = time.perf_counter()
    
    # 限制并发连接数
    limits = httpx.Limits(max_connections=TOTAL_TASKS, max_keepalive_connections=20)
    async with httpx.AsyncClient(limits=limits, timeout=300.0) as client:
        # 创建 100 个并发任务
        tasks = [send_embedding_request(client, i, payload, headers) for i in range(1, TOTAL_TASKS + 1)]
        # 并发执行
        latencies = await asyncio.gather(*tasks)
    
    end_total = time.perf_counter()
    total_duration = end_total - start_total
    
    # 过滤掉失败的任务（None）
    valid_latencies = [l for l in latencies if l is not None]
    success_count = len(valid_latencies)
    error_count = TOTAL_TASKS - success_count
    
    print("-" * 70)
    print("并发测试结果摘要:")
    print(f"总耗时 (从发起第1个到最后一个结束): {total_duration:.2f} 秒")
    print(f"成功任务: {success_count}/{TOTAL_TASKS}")
    print(f"失败任务: {error_count}/{TOTAL_TASKS}")
    
    if valid_latencies:
        avg_latency = sum(valid_latencies) / success_count
        max_latency = max(valid_latencies)
        min_latency = min(valid_latencies)
        
        valid_latencies.sort()
        p95_latency = valid_latencies[int(success_count * 0.95)]
        p50_latency = valid_latencies[int(success_count * 0.50)]
        
        print(f"平均响应时间 (Latency): {avg_latency:.2f} ms")
        print(f"P50 响应时间: {p50_latency:.2f} ms")
        print(f"P95 响应时间: {p95_latency:.2f} ms")
        print(f"最大响应时间: {max_latency:.2f} ms")
        print(f"最小响应时间: {min_latency:.2f} ms")
        
    if success_count > 0:
        total_tokens = success_count * TARGET_TOKENS
        # 注意：这里的吞吐量计算是基于总耗时的并发处理能力
        tokens_per_sec = total_tokens / total_duration
        print(f"并发整体吞吐量: {tokens_per_sec:.2f} tokens/sec")

if __name__ == "__main__":
    asyncio.run(run_concurrent_test())
