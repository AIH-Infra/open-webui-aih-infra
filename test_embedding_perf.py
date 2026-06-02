import time
import httpx
import tiktoken
import json
import sys

# 配置
API_URL = "http://106.15.124.238:18000/v1/embeddings"
MODEL_NAME = "text-embedding-bge-m3"
TOTAL_ROUNDS = 100
TARGET_TOKENS = 2048

def generate_text(token_count):
    # 使用 cl100k_base 编码（常用与 GPT-4/bge 等）
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
    except Exception:
        # 如果无法获取特定编码，回退到默认
        encoding = tiktoken.get_encoding("gpt2")
        
    # 生成一些重复的文本直到达到目标长度
    base_text = "Testing connectivity and speed for embedding model. This is a benchmark test. "
    text = base_text
    while len(encoding.encode(text)) < token_count:
        text += base_text
    
    # 裁剪到精确的 token 数量
    tokens = encoding.encode(text)[:token_count]
    return encoding.decode(tokens)

def run_test():
    print(f"正在准备测试文本 ({TARGET_TOKENS} tokens)...")
    test_text = generate_text(TARGET_TOKENS)
    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL_NAME,
        "input": test_text
    }
    
    latencies = []
    success_count = 0
    error_count = 0
    
    print(f"开始测试: {TOTAL_ROUNDS} 轮请求对模型 {MODEL_NAME} at {API_URL}")
    print("-" * 60)
    
    start_total = time.perf_counter()
    
    for i in range(1, TOTAL_ROUNDS + 1):
        round_start = time.perf_counter()
        try:
            # 增加超时时间，2048 token 的 embedding 可能需要一些时间
            # 使用 httpx 进行同步请求
            with httpx.Client(timeout=60.0) as client:
                response = client.post(API_URL, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
            
            round_end = time.perf_counter()
            latency = (round_end - round_start) * 1000 # ms
            latencies.append(latency)
            success_count += 1
            print(f"轮次 {i:3d}/{TOTAL_ROUNDS}: 成功 - 耗时 {latency:8.2f} ms")
            
        except Exception as e:
            error_count += 1
            print(f"轮次 {i:3d}/{TOTAL_ROUNDS}: 失败 - 错误: {str(e)}")
            
    end_total = time.perf_counter()
    total_duration = end_total - start_total
    
    print("-" * 60)
    print("测试结果摘要:")
    print(f"总耗时: {total_duration:.2f} 秒")
    print(f"成功轮次: {success_count}/{TOTAL_ROUNDS}")
    print(f"失败轮次: {error_count}/{TOTAL_ROUNDS}")
    
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)
        # 排序以计算 P95
        latencies.sort()
        p95_latency = latencies[int(len(latencies) * 0.95)]
        
        print(f"平均响应时间: {avg_latency:.2f} ms")
        print(f"P95 响应时间: {p95_latency:.2f} ms")
        print(f"最大响应时间: {max_latency:.2f} ms")
        print(f"最小响应时间: {min_latency:.2f} ms")
        
    if success_count > 0:
        total_tokens = success_count * TARGET_TOKENS
        tokens_per_sec = total_tokens / total_duration
        print(f"吞吐量: {tokens_per_sec:.2f} tokens/sec")

if __name__ == "__main__":
    run_test()
