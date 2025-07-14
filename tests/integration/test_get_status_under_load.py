import pytest
import time
import random
import logging
import logging.config
import multiprocessing
from scripts import get_status

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

def _get_mock_run(unique_id: int):
    return {
        "run_id": f"run_id_{unique_id}",
        "label": f"Run {unique_id}",
        "status": "ACTIVE",
    }

class ListRuns():
    LIST_RUNS_LOCK = multiprocessing.Lock()
    LOCKING_FAILURES = list()
    LOCK_EVENT = list()

    def __init__(self):
        self.data = [{"runs": [_get_mock_run(n) for n in range(100)]}]
        self.returned = []
        # self.fetching = False

    def __call__(self, client, params):
        lck = self.LIST_RUNS_LOCK.acquire(block=False)
        if lck is False:
            print("Locking Failure.")
            self.LOCKING_FAILURES.append(time.time())
            return
        self.LOCK_EVENT.append(time.time())
        time.sleep(1)
        self.LIST_RUNS_LOCK.release()
        yield from self.data
    
    def get_run_id(self):
        if len(self.returned) >= len(self.data[0]["runs"]):
            raise Exception("Out of run ids! Please increase the number!")
        run_id = self.data[0]["runs"][len(self.returned)]["run_id"]
        self.returned.append(run_id)
        print(f"USING {run_id}")
        return run_id

mocked_list_runs = ListRuns()

def iterate_over(*args):
    variation = random.randint(0, 3)
    start_time = time.time()

    setattr(get_status, 'client_list_runs', mocked_list_runs)
    # print(f"Running with {args}")

    iters = 0
    while start_time + variation + 5 > time.time():
        print(".", end="", flush=True)
        get_status.get_run(*args)
        iters += 1
        # time.sleep(1)
    print(f"Finished with {iters} iterations.", end="")

    print(f"Locking Failures: {len(mocked_list_runs.LOCKING_FAILURES)}")

@pytest.mark.slow
def test_get_status_100_processes():

    num_processes = 100
    interval = 0
    cache_filename = "load_test.sqlite"

    engine = create_engine(f"sqlite:///{cache_filename}")
    get_status.Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        objects = session.query(get_status.Lock).delete()
        session.commit()

    processes = []
    print("Spinning up processses", end="")
    for i in range(num_processes):
        p = multiprocessing.Process(target=iterate_over, args=(mocked_list_runs.get_run_id(), .1, cache_filename, False))
        processes.append(p)
        p.start()
        print(".", end="", flush=True)

    # Wait for all processes to complete
    for p in processes:
        p.join()

    # assert not LOCKING_FAILURES
    with SessionLocal() as session:


        locks = list(session.query(get_status.Lock))
        aborted = [lock for lock in locks if lock.aborted]


        # print(f"Checking integity of {len(locks)} locks...")
        for idx, lock in enumerate(locks):
            if idx + 1 == len(locks):
                break

            next_lock = locks[idx + 1]
            assert lock.completion_time, f"Lock {lock.id} did not finish!"
            # assert lock.completion_time < next_lock.start_time, f"Lock {next_lock.id} acquired before {lock.id} completed."
    print(f'Processed {len(mocked_list_runs.LOCK_EVENT)} events. {len(locks)} Total Locks. {len(aborted)} Aborted. {len(aborted) / len(locks) * 100}% Aborts')

    assert mocked_list_runs.LOCKING_FAILURES == []
    lock_times = []
    last_le = None
    for le in mocked_list_runs.LOCK_EVENT:
        if last_le is None:
            continue
        lock_times.append(round(le - last_le), 3)
        last_le = le
    print(f"Lock times between lock events: {lock_times}")


if __name__ == "__main__":
    test_get_status_100_processes()