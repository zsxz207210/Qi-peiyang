import psycopg2
import time
import sys

def main():
    num_messages = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    conn = psycopg2.connect(
        host="192.168.8.104",
        database="kafka_test",
        user="kafka_user",
        password="password123"
    )
    cursor = conn.cursor()
    batch_size = 1000
    batch = []
    
    start_time = time.time()
    last_print = time.time()
    processed = 0
    
    for i in range(num_messages):
        batch.append((f"Message {i}",))
        processed += 1
        
        if len(batch) >= batch_size:
            cursor.executemany(
                "INSERT INTO messages (content) VALUES (%s)",
                batch
            )
            conn.commit()
            batch = []
        
        # 每秒打印一次进度
        if time.time() - last_print > 1.0:
            elapsed = time.time() - start_time
            print(f"[DIRECT] Processed {processed} messages ({processed/elapsed:.2f} msg/s)")
            last_print = time.time()
    
    # 处理剩余消息
    if batch:
        cursor.executemany(
            "INSERT INTO messages (content) VALUES (%s)",
            batch
        )
        conn.commit()
    
    elapsed = time.time() - start_time
    print(f"\n[DIRECT] Total processed {num_messages} messages in {elapsed:.2f} seconds")
    print(f"[DIRECT] Final throughput: {num_messages/elapsed:.2f} msg/s")
    cursor.close()
    conn.close()

if __name__ == "__main__":
main()
