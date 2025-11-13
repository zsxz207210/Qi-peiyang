from confluent_kafka import Consumer
import psycopg2
import psycopg2.pool  # 新增：连接池模块
import json
import time
import sys
from concurrent.futures import ThreadPoolExecutor  # 新增：线程池模块

# === Step 1: 配置数据库连接池 ===
db_pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=5,          # 最小空闲连接数
    maxconn=20,         # 最大连接数（根据PostgreSQL max_connections调整）
    host="192.168.8.104",
    database="kafka_test",
    user="kafka_user",
    password="password123"
)

def get_db_connection():
    """从连接池获取数据库连接"""
    return db_pool.getconn()

def release_db_connection(conn):
    """归还连接到连接池"""
    db_pool.putconn(conn)

# === Step 2: 线程池配置 ===
executor = ThreadPoolExecutor(max_workers=10)  # 根据CPU核心数调整

# === Step 3: 消息处理函数（线程池任务） ===
def process_message_batch(batch):
    """批量插入消息到数据库"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 批量插入：提取JSON中的'content'字段
            data = [(json.loads(msg.decode('utf-8'))['content'],) for msg in batch]
            cur.executemany("INSERT INTO messages (content) VALUES (%s)", data)
            conn.commit()
    except Exception as e:
        print(f"[ERROR] Database error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            release_db_connection(conn)

# === Step 4: Kafka消费者主程序 ===
conf = {
    'bootstrap.servers': '192.168.8.101:9092,192.168.8.102:9092,192.168.8.103:9092',
    'group.id': 'db-writer-group',
    'auto.offset.reset': 'earliest',
    'max.poll.interval.ms': 300000
}

if __name__ == "__main__":
    consumer = Consumer(conf)
    consumer.subscribe(['test-topic'])
    
    batch_size = 1000  # 每个批次大小
    batch = []
    msg_count = 0
    start_time = time.time()
    last_print = time.time()

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                # 无新消息时检查是否需要提交剩余批次
                if batch:
                    executor.submit(process_message_batch, batch)
                    batch = []
                continue
                
            if msg.error():
                print(f"Consumer error: {msg.error()}")
                continue
                
            batch.append(msg.value())
            msg_count += 1
            
            # 达到批处理阈值时提交到线程池
            if len(batch) >= batch_size:
                executor.submit(process_message_batch, batch)
                batch = []
                
            # 每秒打印吞吐量
            if time.time() - last_print > 1.0:
                elapsed = time.time() - start_time
                print(f"[CONSUMER] Processed {msg_count} messages ({msg_count/elapsed:.2f} msg/s)")
                last_print = time.time()
                
    except KeyboardInterrupt:
        print("\nStopping consumer...")
    finally:
        # 提交剩余未处理的消息
        if batch:
            executor.submit(process_message_batch, batch)
        
        # 等待所有线程任务完成
        executor.shutdown(wait=True)
        
        # 关闭资源
        elapsed = time.time() - start_time
        print(f"\n[CONSUMER] Total processed {msg_count} messages in {elapsed:.2f} seconds")
        print(f"[CONSUMER] Final throughput: {msg_count/elapsed:.2f} msg/s")
        
        consumer.close()
        # 连接池无需手动关闭，会在程序退出时自动释放
