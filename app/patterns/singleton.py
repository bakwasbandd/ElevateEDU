import threading


class SingletonMeta(type):
    """Thread-safe Singleton metaclass.
    Any class using this as its metaclass will only ever have one instance.
    """
    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]

    @classmethod
    def reset(mcs, cls):
        """Tear down the singleton — mainly useful for testing."""
        with mcs._lock:
            mcs._instances.pop(cls, None)
