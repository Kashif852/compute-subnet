import ast
import os
import subprocess
import threading
import queue
import time
import traceback
import uuid
import bittensor as bt


class RequestSpecsProcessor:
    def __init__(self):
        self.request_queue = queue.Queue()
        self.results_dict = {}
        # Start the worker thread
        threading.Thread(target=self.worker, daemon=True).start()

    def worker(self):
        while True:
            # Get a request, its associated request_id, and event from the queue
            app_data, request_id, done_event = self.request_queue.get()
            try:
                # Process the request
                self.process_request(app_data, request_id)
            finally:
                # Mark the processed request as done
                self.request_queue.task_done()
                # Set the event to signal that the processing is complete
                done_event.set()
            time.sleep(1)

    def process_request(self, app_data, request_id):
        bt.logging.info(f"💻 Specs query started {request_id} ...")
        try:
            app_data = ast.literal_eval(app_data)

            main_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(main_dir, f"app_{request_id}")  # Use a unique file name

            # Write the bytes data to a file
            with open(file_path, "wb") as file:
                file.write(app_data)
            subprocess.run(f"chmod +x {file_path}", shell=True, check=True)
            result = subprocess.check_output([file_path], shell=True, text=True)
        except Exception as e:
            traceback.print_exc()
            result = {"process_request error": str(e)}
        finally:
            # Clean up the file after execution
            if os.path.exists(file_path):
                os.remove(file_path)

        # Store the result in the shared dictionary
        self.results_dict[request_id] = result

    def get_respond(self, app_data):
        try:
            # Generate a unique identifier for the request
            request_id = str(uuid.uuid4())
            # Create an event that will be set when the request is processed
            done_event = threading.Event()
            # Add the request, request_id, and the event to the queue
            bt.logging.info(f"💻 Specs query queuing {request_id} ...")
            self.request_queue.put((app_data, request_id, done_event))
            # Wait for the request to be processed
            done_event.wait()  # This will block until the event is set
            # Retrieve the result from the results_dict
            result = self.results_dict.pop(request_id)  # Remove the result from the dictionary
            bt.logging.info(f"💻 Specs query finalized {request_id} ...")
            return result
        except Exception as e:
            traceback.print_exc()
            return {"get_respond error": str(e)}
