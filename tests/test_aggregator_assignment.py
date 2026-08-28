import json
import os
import unittest
from unittest.mock import patch

from kafka import TopicPartition

from services.aggregator.main import AssignmentLogger, serialize_partitions
from services.common.kafka_config import kafka_security_config


class AssignmentLoggingTests(unittest.TestCase):
    def test_partitions_are_sorted_and_serialized(self) -> None:
        partitions = [TopicPartition("topic-b", 1), TopicPartition("topic-a", 0)]
        self.assertEqual(
            serialize_partitions(partitions),
            [
                {"topic": "topic-a", "partition": 0},
                {"topic": "topic-b", "partition": 1},
            ],
        )

    @patch("services.aggregator.main.logger")
    def test_assignment_callback_logs_structured_partitions(self, logger) -> None:
        AssignmentLogger().on_partitions_assigned([TopicPartition("topic-a", 0)])
        logger.info.assert_called_once()
        self.assertEqual(logger.info.call_args.args[0], "partitions_assigned")
        self.assertEqual(
            logger.info.call_args.kwargs["extra"]["topic_partitions"],
            [{"topic": "topic-a", "partition": 0}],
        )


class KafkaSecurityConfigTests(unittest.TestCase):
    def test_plaintext_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(kafka_security_config(), {"security_protocol": "PLAINTEXT"})

    def test_event_hubs_sasl(self) -> None:
        with patch.dict(
            os.environ,
            {
                "KAFKA_SECURITY_PROTOCOL": "SASL_SSL",
                "KAFKA_SASL_PASSWORD": "secret",
            },
            clear=True,
        ):
            config = kafka_security_config()
        self.assertEqual(config["sasl_mechanism"], "PLAIN")
        self.assertEqual(config["sasl_plain_username"], "$ConnectionString")
        self.assertEqual(config["sasl_plain_password"], "secret")


if __name__ == "__main__":
    unittest.main()
