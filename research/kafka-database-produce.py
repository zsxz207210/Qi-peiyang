from confluent_kafka import Producer
import json
import time
import sys

conf = {
    'bootstrap.servers': '192.168.8.101:9092,192.168.8.102:9092,192.168.8.103:9092',
    'compression.type': 'lz4',
    'batch.size': 16384,
    'linger.ms': 10
}

def delivery_report(err, msg):
    if err:
        print(f'Message delivery failed: {err}')

if __name__ == "__main__":
    num_messages = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    producer = Producer(conf)
    topic = 'test-topic'
    
    start_time = time.time()
    
    for i in range(num_messages):
        data = {
            "id": i,
            "content": f"Message {i}",
            "timestamp": int(time.time() * 1000)
        }
        producer.produce(
            topic, 
            key=str(i), 
            value=json.dumps(data), 
            callback=delivery_report
        )
    
    producer.flush()
    elapsed = time.time() - start_time
    
    print(f"[PRODUCER] Sent {num_messages} messages in {elapsed:.2f} seconds")
    print(f"[PRODUCER] Throughput: {num_messages/elapsed:.2f} msg/s")
