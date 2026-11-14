import logging
import signal
import threading
import uuid

from app.services.analysis.orchestrator import worker_loop


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    stop_event = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stop_event.set())
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, lambda *_: stop_event.set())
    worker_loop(stop_event, f"worker-{uuid.uuid4().hex[:12]}")


if __name__ == "__main__":
    main()
