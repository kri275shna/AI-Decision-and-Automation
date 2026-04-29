import queue
import threading
import time
from app.utils.logger import logger

class TaskQueue:
    def __init__(self, max_retries=3):
        self.queue = queue.PriorityQueue()
        self.max_retries = max_retries
        self.worker_thread = None
        self.running = False
        self.processor = None

    def set_processor(self, processor_func):
        self.processor = processor_func

    def start(self):
        if not self.running:
            self.running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()

    def stop(self):
        self.running = False
        if self.worker_thread:
            self.worker_thread.join()

    def enqueue(self, task_data, retry_count=0):
        delay = 0 if retry_count == 0 else 2 ** (retry_count - 1)
        execute_at = time.time() + delay
        priority = execute_at
        self.queue.put((priority, time.time(), {"task_data": task_data, "retry_count": retry_count}))
        logger.info(f"Task enqueued", extra={"request_id": task_data.get("request_id"), "retry_count": retry_count})

    def _worker_loop(self):
        while self.running:
            try:
                if self.queue.empty():
                    time.sleep(0.5)
                    continue

                priority, ts, item = self.queue.get(timeout=1)
                
                if time.time() < priority:
                    self.queue.put((priority, ts, item))
                    time.sleep(0.5)
                    continue
                
                task_data = item["task_data"]
                retry_count = item["retry_count"]
                request_id = task_data.get("request_id")
                
                logger.info("Processing task", extra={"request_id": request_id, "retry_count": retry_count})
                
                try:
                    if self.processor:
                        self.processor(task_data)
                    self.queue.task_done()
                except Exception as e:
                    logger.error(f"Task processing failed: {str(e)}", extra={"request_id": request_id})
                    if retry_count < self.max_retries:
                        self.enqueue(task_data, retry_count + 1)
                    else:
                        logger.error("Max retries reached. Task dead-lettered.", extra={"request_id": request_id})
                        self._handle_dead_letter(task_data, str(e))
                    self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker loop error: {str(e)}")
                time.sleep(1)

    def _handle_dead_letter(self, task_data, error):
        if self.processor:
            task_data["_dead_letter"] = True
            task_data["_error"] = error
            try:
                self.processor(task_data)
            except Exception as e:
                logger.error(f"Dead letter handling failed: {str(e)}")

task_queue = TaskQueue()
