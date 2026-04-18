import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass
class ShipmentEvent:
    event_id: str
    shipment_id: str
    domain: str
    event_type: str
    occurred_at: str
    location: str
    details: Dict[str, Any]

    @classmethod
    def create(
        cls,
        shipment_id: str,
        domain: str,
        event_type: str,
        location: str,
        details: Dict[str, Any],
    ) -> "ShipmentEvent":
        return cls(
            event_id=str(uuid.uuid4()),
            shipment_id=shipment_id,
            domain=domain,
            event_type=event_type,
            occurred_at=datetime.now(timezone.utc).isoformat(),
            location=location,
            details=details,
        )

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, payload: str) -> "ShipmentEvent":
        data = json.loads(payload)
        return cls(**data)
