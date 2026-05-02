import threading
import time
import json
import os
import random
from app import app, save_participations, load_participations, load_users, save_users, DATA_FILE, PARTICIPATIONS_FILE, USER_FILE
from werkzeug.security import generate_password_hash

# Configuration
NUM_THREADS = 20  # Simultaneous users
OPS_PER_THREAD = 10 # Actions per user
TOTAL_ACTIONS = NUM_THREADS * OPS_PER_THREAD

def simulate_user_action(user_id):
    """Simulates a user submitting a participation."""
    for i in range(OPS_PER_THREAD):
        try:
            with app.app_context():
                # Simulate loading and saving participations (which has the lock)
                parts = load_participations()
                new_part = {
                    "username": f"student_{user_id}",
                    "event_id": f"event_{random.randint(1, 5)}",
                    "status": "approved",
                    "timestamp": time.time()
                }
                parts.append(new_part)
                save_participations(parts)
                # Small sleep to simulate network latency
                time.sleep(0.01)
        except Exception as e:
            print(f"Error in thread {user_id}: {e}")

def run_full_scale_test():
    print(f"Starting Full Scale Concurrency Test...")
    print(f"Simulating {NUM_THREADS} concurrent users performing {OPS_PER_THREAD} actions each.")
    print(f"Total target operations: {TOTAL_ACTIONS}")
    print("-" * 50)
    
    start_time = time.time()
    
    threads = []
    for i in range(NUM_THREADS):
        t = threading.Thread(target=simulate_user_action, args=(i,))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    end_time = time.time()
    duration = end_time - start_time
    
    # Verify results
    final_parts = load_participations()
    print("-" * 50)
    print(f"Test Completed in {duration:.2f} seconds.")
    print(f"Total Participations in file: {len(final_parts)}")
    print(f"Speed: {TOTAL_ACTIONS / duration:.2f} operations/second")
    print(f"Data Integrity: {'OK' if len(final_parts) >= TOTAL_ACTIONS else 'FAIL'}")
    print("-" * 50)

if __name__ == "__main__":
    # Ensure files exist
    if not os.path.exists(PARTICIPATIONS_FILE):
        save_json(PARTICIPATIONS_FILE, [])
        
    run_full_scale_test()
