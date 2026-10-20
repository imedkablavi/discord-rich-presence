import threading

from ui_dispatch import UIThreadDispatcher


def test_post_does_not_execute_callback_on_worker_thread():
    dispatcher = UIThreadDispatcher()
    caller_thread = threading.get_ident()
    executed = []

    def worker():
        dispatcher.post(lambda: executed.append(threading.get_ident()))

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(timeout=1)

    assert not thread.is_alive()
    assert executed == []
    callbacks = dispatcher.take_pending()
    assert len(callbacks) == 1

    for callback in callbacks:
        callback()

    assert executed == [caller_thread]


def test_dispatcher_preserves_order_and_bounds_each_drain():
    dispatcher = UIThreadDispatcher()
    executed = []
    for value in range(5):
        dispatcher.post(lambda value=value: executed.append(value))

    first = dispatcher.take_pending(limit=2)
    assert len(first) == 2
    assert dispatcher.take_pending(limit=0) == []
    remaining = dispatcher.take_pending(limit=64)
    assert len(remaining) == 3

    for callback in first + remaining:
        callback()
    assert executed == [0, 1, 2, 3, 4]
