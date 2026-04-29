import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "name": record.name
        }
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        if hasattr(record, "state"):
            log_record["state"] = record.state
        if hasattr(record, "latency"):
            log_record["latency"] = record.latency
        if record.exc_info:
            log_record["error"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

logger = logging.getLogger("ai_platform")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
