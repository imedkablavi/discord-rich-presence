import queue
import threading
import time

from social_sdk_transport import SocialSDKPresence


def test_terminate_process_joins_reader_thread_and_resets_queue():
    transport = SocialSDKPresence('123456789')
    started = threading.Event()

    def reader():
        started.set()
        time.sleep(0.05)

    thread = threading.Thread(target=reader, name='qa-social-reader', daemon=True)
    thread.start()
    assert started.wait(1.0)

    old_queue = transport._responses
    transport._reader_thread = thread
    transport._process = None
    transport._terminate_process()

    assert transport._reader_thread is None
    assert not thread.is_alive()
    assert transport._responses is not old_queue


def test_terminate_process_is_idempotent_without_helper():
    transport = SocialSDKPresence('123456789')
    transport._terminate_process()
    transport._terminate_process()
    assert transport._process is None
    assert transport._reader_thread is None



def test_reader_treats_closed_stdout_as_normal_shutdown():
    class ClosedStdout:
        def __iter__(self):
            return self

        def __next__(self):
            raise ValueError("I/O operation on closed file")

    class FakeProcess:
        stdout = ClosedStdout()

    transport = SocialSDKPresence('123456789')
    transport._process = FakeProcess()
    transport._responses = queue.Queue(maxsize=16)

    # A closed text stream should be consumed as a normal reader shutdown and
    # leave the sentinel expected by any waiting command.
    transport._read_responses()

    assert transport._responses.get_nowait() is None
