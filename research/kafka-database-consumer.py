from confluent_kafka import Consumer
import psycopg2
import json
import time
import sys

def create_db_conn():
    return psycopg2.connect(
        host="192.168.8.104",
        database="kafka_test",
        user="kafka_user",
        password="password123"
    )

conf = {
    'bootstrap.servers': '192.168.8.101:9092,192.168.8.102:9092,192.168.8.103:9092',
    'group.id': 'db-writer-group',
    'auto.offset.reset': 'earliest',
    'max.poll.interval.ms': 300000
}

if __name__ == "__main__":
    consumer = Consumer(conf)
    consumer.subscribe(['test-topic'])
    conn = create_db_conn()
    cursor = conn.cursor()
    batch_size = 1000
    batch = []
    msg_count = 0
    
    start_time = time.time()
    last_print = time.time()
    
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                if batch:
                    cursor.executemany(
                        "INSERT INTO messages (content) VALUES (%s)",
                        [(json.loads(m.decode('utf-8'))['content'],) for m in batch]
                    )
                    conn.commit()
                    batch = []
                continue
                
            if msg.error():
                print(f"Consumer error: {msg.error()}")
                continue
                
            batch.append(msg.value())
            msg_count += 1
            
            if len(batch) >= batch_size:
                cursor.executemany(
                    "INSERT INTO messages (content) VALUES (%s)",
                    [(json.loads(m.decode('utf-8'))['content'],) for m in batch]
                )
                conn.commit()
                batch = []
                
            # 每秒打印一次进度
            if time.time() - last_print > 1.0:
                elapsed = time.time() - start_time
                print(f"[CONSUMER] Processed {msg_count} messages ({msg_count/elapsed:.2f} msg/s)")
                last_print = time.time()
                
    except KeyboardInterrupt:
        print("\nStopping consumer...")
    finally:
        # 处理剩余消息
        if batch:
            cursor.executemany(
                "INSERT INTO messages (content) VALUES (%s)",
                [(json.loads(m.decode('utf-8'))['content'],) for m in batch]
            )
            conn.commit()
        
        elapsed = time.time() - start_time
        print(f"\n[CONSUMER] Total processed {msg_count} messages in {elapsed:.2f} seconds")
        print(f"[CONSUMER] Final throughput: {msg_count/elapsed:.2f} msg/s")
        
        cursor.close()
        conn.close()
        consumer.close()
