from confluent_kafka import Consumer, Producer
from confluent_kafka.admin import AdminClient, NewTopic

from logistics_agents.domain.models import ShipmentNotification

SHIPMENT_TOPIC = "shipment.notifications"


def _ensure_topic(bootstrap: str) -> None:
    admin = AdminClient({"bootstrap.servers": bootstrap})
    existing = admin.list_topics(timeout=10).topics
    if SHIPMENT_TOPIC not in existing:
        futures = admin.create_topics([NewTopic(SHIPMENT_TOPIC, num_partitions=1, replication_factor=1)])
        for future in futures.values():
            try:
                future.result()
            except Exception:
                pass  # already exists / concurrent create


def publish_notification(bootstrap: str, asn: ShipmentNotification) -> None:
    _ensure_topic(bootstrap)
    producer = Producer({"bootstrap.servers": bootstrap})
    producer.produce(SHIPMENT_TOPIC, value=asn.model_dump_json().encode("utf-8"))
    producer.flush(10)


def consume_one(
    bootstrap: str, group_id: str, timeout_s: float = 10.0
) -> ShipmentNotification | None:
    _ensure_topic(bootstrap)
    consumer = Consumer(
        {
            "bootstrap.servers": bootstrap,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
        }
    )
    consumer.subscribe([SHIPMENT_TOPIC])
    try:
        msg = consumer.poll(timeout_s)
        if msg is None or msg.error():
            return None
        return ShipmentNotification.model_validate_json(msg.value().decode("utf-8"))
    finally:
        consumer.close()
