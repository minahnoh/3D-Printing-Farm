from config_SimPy import *


class Worker:
    def __init__(self, id_worker, name_worker, processing_time):
        self.id_worker = id_worker
        self.name_worker = name_worker
        self.available_status = True
        self.working_job = None
        self.processing_time = processing_time
        self.busy_time = 0
        self.last_status_change = 0


class Worker_Inspect(Worker):
    def __init__(self, id_worker):
        super().__init__(
            id_worker, f"Inspector_{id_worker}", PROC_TIME_INSPECT)


class Machine:
    def __init__(self, id_machine, id_process, name_machine, processing_time, capacity_jobs=1):
        self.id_machine = id_machine
        self.id_process = id_process
        self.name_machine = name_machine
        self.available_status = True
        self.list_working_jobs = []
        self.capacity_jobs = capacity_jobs
        self.processing_time = processing_time
        self.busy_time = 0
        self.last_status_change = 0


class Mach_3DPrint(Machine):
    def __init__(self, id_machine):
        super().__init__(id_machine, "Proc_Build",
                         f"3DPrinter_{id_machine}", PROC_TIME_BUILD, CAPACITY_MACHINE_BUILD)


class Mach_Wash(Machine):
    def __init__(self, id_machine):
        super().__init__(id_machine, "Proc_Wash",
                         f"Washer_{id_machine}", PROC_TIME_WASH, CAPACITY_MACHINE_WASH)


class Mach_Dry(Machine):
    def __init__(self, id_machine):
        super().__init__(id_machine, "Proc_Dry",
                         f"Dryer_{id_machine}", PROC_TIME_DRY, CAPACITY_MACHINE_DRY)
