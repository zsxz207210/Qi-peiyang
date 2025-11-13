from locust import User, task, between, events
from confluent_kafka import Producer, KafkaException
import random
import string
import time

class KafkaProducerUser(User):
    wait_time = between(0.1, 0.5)
    _producer = None  # 单例 Producer

    def on_start(self):
        if KafkaProducerUser._producer is None:
            KafkaProducerUser._producer = Producer({
                'bootstrap.servers': '192.168.8.101:9092,192.168.8.102:9092,192.168.8.103:9092,192.168.8.104:9092,192.168.8.105:9092',
                'client.id': 'shared-producer',
                'acks': 'all',  # 确保所有副本确认
                'retries': 5,
                'retry.backoff.ms': 1000,
                'enable.idempotence': True,  # 防止消息重复
            })
        self.producer = KafkaProducerUser._producer

    @task
    def send_message(self):
        payload = ''.join(random.choices(string.ascii_letters + string.digits, k=100))
        start_time = time.time()

        def delivery_report(err, msg):
            if err:
                total_time = (time.time() - start_time) * 1000
                events.request.fire(
                    request_type="Kafka",
                    name="produce",
                    response_time=total_time,
                    response_length=0,
                    exception=err
                )
                print(f"❌ Failed to deliver: {err}")
            else:
                total_time = (time.time() - start_time) * 1000
                events.request.fire(
                    request_type="Kafka",
                    name="produce",
                    response_time=total_time,
                    response_length=len(msg.value()),
                    success=True
                )
                print(f"✅ Delivered to {msg.topic()} [{msg.partition()}]")

        try:
            self.producer.produce('load_test',  value=payload, callback=delivery_report)
            self.producer.poll(1)  # 增加等待时间
        except Exception as e:
            total_time = (time.time() - start_time) * 1000
            events.request.fire(
                request_type="Kafka",
                name="produce",
                response_time=total_time,
                response_length=0,
                exception=e
            )

    def on_stop(self):
        try:
            self.producer.flush(timeout=10)  # 确保消息发送完成
        except KafkaException as e:
            print(f"⚠️ Flush error: {e}")
