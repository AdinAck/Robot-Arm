from threading import Thread

from typing import Callable

def threaded_callback(function: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        Thread(target = function, args = args, kwargs = kwargs, daemon = True).start()

    return wrapper