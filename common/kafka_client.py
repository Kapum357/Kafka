"""Kafka producer/consumer helpers for Confluent Cloud."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Iterable

from confluent_kafka import Consumer, Producer

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class KafkaConfig:
    bootstrap_servers: str
    sasl_username: str | None
    sasl_password: str | None
    sasl_mechanism: str = "PLAIN"
    security_protocol: str = "SASL_SSL"

    @classmethod
    def from_env(cls) -> "KafkaConfig":
        return cls(
            bootstrap_servers=os.environ["KAFKA_BOOTSTRAP_SERVERS"],
            sasl_username=os.getenv("KAFKA_API_KEY"),
            sasl_password=os.getenv("KAFKA_API_SECRET"),
            sasl_mechanism=os.getenv("KAFKA_SASL_MECHANISM", "PLAIN"),
            security_protocol=os.getenv("KAFKA_SECURITY_PROTOCOL", "SASL_SSL" if os.getenv("KAFKA_API_KEY") else "PLAINTEXT"),
        )

    def producer_conf(self) -> dict[str, Any]:
        conf: dict[str, Any] = {
            "bootstrap.servers": self.bootstrap_servers,
            "security.protocol": self.security_protocol,
            "client.id": os.getenv("KAFKA_CLIENT_ID", "django-microservices"),
            "linger.ms": "20",
            "acks": "all",
            "enable.idempotence": True,
        }
        if self.sasl_username and self.sasl_password:
            conf.update({
                "sasl.mechanisms": self.sasl_mechanism,
                "sasl.username": self.sasl_username,
                "sasl.password": self.sasl_password,
            })
        return conf

    def consumer_conf(self, group_id: str) -> dict[str, Any]:
        conf: dict[str, Any] = {
            "bootstrap.servers": self.bootstrap_servers,
            "security.protocol": self.security_protocol,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
        if self.sasl_username and self.sasl_password:
            conf.update({
                "sasl.mechanisms": self.sasl_mechanism,
                "sasl.username": self.sasl_username,
                "sasl.password": self.sasl_password,
            })
        return conf


class KafkaEventPublisher:
    def __init__(self, config: KafkaConfig | None = None) -> None:
        self.config = config or KafkaConfig.from_env()
        self.producer = Producer(self.config.producer_conf())

    def publish(self, topic: str, payload: dict, key: str | None = None) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.producer.produce(topic, key=key, value=body)
        self.producer.flush(10)
        logger.info("Published event to topic=%s key=%s payload=%s", topic, key, payload)


class KafkaEventConsumer:
    def __init__(self, topics: Iterable[str], group_id: str, config: KafkaConfig | None = None) -> None:
        self.config = config or KafkaConfig.from_env()
        self.consumer = Consumer(self.config.consumer_conf(group_id))
        self.consumer.subscribe(list(topics))

    def poll(self, timeout: float = 1.0):
        return self.consumer.poll(timeout)

    def commit(self, message) -> None:
        self.consumer.commit(message=message, asynchronous=False)

    def close(self) -> None:
        self.consumer.close()
