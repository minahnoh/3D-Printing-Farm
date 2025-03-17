import simpy


class Job:
    def __init__(self, id_job, list_items):
        self.id_job = id_job
        self.workstation = {"Process": None, "Machine": None, "Worker": None}
        self.list_items = list_items
        self.time_processing_start = None
        self.time_processing_end = None
        self.time_waiting_start = None
        self.time_waiting_end = None
        self.is_reprocess = False  # Flag for reprocessed jobs

        # Add processing history to track jobs across all processes
        self.processing_history = []  # Will store each process step details


class JobStore(simpy.Store):
    """Job queue management class that inherits SimPy Store"""

    def __init__(self, env, name="JobStore"):
        super().__init__(env)
        self.name = name
        self.queue_length_history = []  # Track queue length history

    def put(self, item):
        """Add Job to Store (override)"""
        result = super().put(item)
        # Record queue length
        self.queue_length_history.append((self._env.now, len(self.items)))
        return result

    def get(self):
        """Get Job from queue (override)"""
        result = super().get()
        # Record queue length when getting result

        # Use event chain instead of callback
        def process_get(env, result):
            job = yield result
            self.queue_length_history.append((self._env.now, len(self.items)))
            return job

        return self._env.process(process_get(self._env, result))

    @property
    def is_empty(self):
        """Check if queue is empty"""
        return len(self.items) == 0

    @property
    def size(self):
        """Current queue size"""
        return len(self.items)
