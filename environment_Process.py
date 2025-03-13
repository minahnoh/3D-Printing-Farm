import random
from config_SimPy import *
from environment_Processor import Worker, Worker_Inspect, Machine, Mach_3DPrint, Mach_Wash, Mach_Dry


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


class Process:
    def __init__(self, id_process, env, manager):
        self.id_process = id_process
        self.env = env
        self.manager = manager
        self.queue = []
        self.list_processors = []
        self.policy_dispatch_from_queue = POLICY_DISPATCH_FROM_QUEUE
        self.queue_length_history = []  # Track queue length over time
        # 주기적 체크 방식에서 이벤트 기반 방식으로 변경하므로 processing 프로세스를 제거

    def add_to_queue(self, job):
        """Add job to the process queue"""
        job.time_waiting_start = self.env.now
        job.workstation["Process"] = self.id_process
        self.queue.append(job)
        # Record queue length
        self.queue_length_history.append((self.env.now, len(self.queue)))

        # Log event - 항상 manager를 통해 logger에 접근
        if self.manager.logger:
            self.manager.logger.log_event(
                "Queue", f"Added Job {job.id_job} to {self.id_process} queue. Queue length: {len(self.queue)}")

        # 큐에 작업이 추가되면 즉시 자원 할당 시도
        self.seize_resources()

    def seize_resources(self):
        """Assign jobs to available processors based on queue policy and start processing"""
        if not self.queue:
            return

        # Sort the queue according to policy
        if self.policy_dispatch_from_queue == "FIFO":
            # Queue is already FIFO by default
            pass
        # Add more queue policies here if needed

        # Find available processors
        available_processors = []
        for p in self.list_processors:
            if isinstance(p, Machine):
                # 기계의 경우 실제 사용 중인 작업 수와 용량을 비교하여 가용성 결정
                if len(p.list_working_jobs) < p.capacity_jobs:
                    available_processors.append(p)
            else:
                # 작업자의 경우 기존 available_status 사용
                if p.available_status:
                    available_processors.append(p)

        # Debug log for available processors
        if self.manager.logger:
            available_names = [p.name_machine if isinstance(
                p, Machine) else p.name_worker for p in available_processors]
            self.manager.logger.log_event(
                "Resource", f"Available processors in {self.id_process}: {', '.join(available_names) if available_names else 'None'}")

        while self.queue and available_processors:
            # Get the first job from queue
            job = self.queue.pop(0)
            job.time_waiting_end = self.env.now

            # Record queue length change
            self.queue_length_history.append((self.env.now, len(self.queue)))

            # Assign to first available processor
            processor = available_processors.pop(0)

            # Set up job with processor
            if isinstance(processor, Machine):
                job.workstation["Machine"] = processor.id_machine
                # Log event
                if self.manager.logger:
                    self.manager.logger.log_event(
                        "Processing", f"Assigning job {job.id_job} to {processor.name_machine}")

                # 작업을 먼저 추가
                processor.list_working_jobs.append(job)

                # 그 후 available_status 업데이트 - 용량이 꽉 찼는지 정확히 체크
                processor.available_status = len(
                    processor.list_working_jobs) < processor.capacity_jobs

                # Resource 상태 디버그 로깅
                if self.manager.logger:
                    self.manager.logger.log_event(
                        "Resource", f"{processor.name_machine} status: working jobs={len(processor.list_working_jobs)}, capacity={processor.capacity_jobs}, available={processor.available_status}")

                # Start processing with resource delay
                self.env.process(self.delay_resources(job, processor))

            elif isinstance(processor, Worker):
                job.workstation["Worker"] = processor.id_worker
                # Log event
                if self.manager.logger:
                    self.manager.logger.log_event(
                        "Processing", f"Assigning job {job.id_job} to {processor.name_worker}")

                # Update processor status
                processor.available_status = False
                processor.working_job = job

                # Start processing with resource delay
                self.env.process(self.delay_resources(job, processor))

    def delay_resources(self, job, processor):
        """Simulate processing time with the resource"""
        # Update busy time tracking for processor
        if isinstance(processor, Machine) or isinstance(processor, Worker):
            if not processor.available_status:
                processor.busy_time += self.env.now - processor.last_status_change
            processor.last_status_change = self.env.now

        # Record start time for this processing step
        job.time_processing_start = self.env.now

        # Record this processing step in job history
        process_step = {
            'process': self.id_process,
            'resource_type': 'Machine' if isinstance(processor, Machine) else 'Worker',
            'resource_id': processor.id_machine if isinstance(processor, Machine) else processor.id_worker,
            'resource_name': processor.name_machine if isinstance(processor, Machine) else processor.name_worker,
            'start_time': job.time_processing_start,
            'end_time': None,  # Will be filled after processing
            'duration': None   # Will be filled after processing
        }

        # Add to job's processing history
        if not hasattr(job, 'processing_history'):
            job.processing_history = []
        job.processing_history.append(process_step)

        # Debug log for job history tracking
        if self.manager.logger:
            self.manager.logger.log_event(
                "Job History", f"Started step for job {job.id_job} on {process_step['resource_name']} at time {self.env.now}")

        # Process the job based on processor type
        if isinstance(processor, Machine):
            # Machine processing
            if self.id_process == "Proc_Build" and isinstance(processor, Mach_3DPrint):
                # Simulate processing time
                yield self.env.timeout(processor.processing_time)

                # Set defect status for items (specific to 3D printing)
                for item in job.list_items:
                    if random.random() < DEFECT_RATE_PROC_BUILD:
                        item.is_defect = True
            else:
                # Regular machine processing
                yield self.env.timeout(processor.processing_time)

        elif isinstance(processor, Worker):
            # Worker processing
            if isinstance(processor, Worker_Inspect):
                # Special processing for inspection workers
                defective_items = []

                # Inspect each item
                for item in job.list_items:
                    # Inspection takes time
                    yield self.env.timeout(processor.processing_time)

                    # If the item was marked as defective in build, identify it here
                    if item.is_defect:
                        defective_items.append(item)
                    else:
                        # Mark item as completed
                        item.is_completed = True

                # Process defective items if found
                if defective_items and self.manager.logger:
                    self.manager.logger.log_event(
                        "Inspection", f"Found {len(defective_items)} defective items in job {job.id_job}")
                    self.manager.process_defective_items(defective_items)
            else:
                # Regular worker processing
                # Process each item in the job
                for item in job.list_items:
                    yield self.env.timeout(processor.processing_time)

        # Update process step with end time and duration
        process_step['end_time'] = self.env.now
        process_step['duration'] = self.env.now - job.time_processing_start

        # Debug log for job history tracking
        if self.manager.logger:
            self.manager.logger.log_event(
                "Job History", f"Completed step for job {job.id_job} on {process_step['resource_name']} at time {self.env.now}")

        # After processing, release resources
        self.release_resources(job, processor, process_step)

    def release_resources(self, job, processor, process_step):
        """Release resources after processing and send job to next process"""
        # Record end time for this processing step
        job.time_processing_end = self.env.now

        # Update process step record
        process_step['end_time'] = job.time_processing_end
        process_step['duration'] = job.time_processing_end - \
            job.time_processing_start

        # Release processor
        if isinstance(processor, Machine):
            processor.list_working_jobs.remove(job)
            processor.available_status = True
            processor.last_status_change = self.env.now

            # Log completion
            if self.manager.logger:
                self.manager.logger.log_event(
                    "Processing", f"Completed processing job {job.id_job} on {processor.name_machine}")

        elif isinstance(processor, Worker):
            processor.working_job = None
            processor.available_status = True
            processor.last_status_change = self.env.now

            # Log completion
            if not isinstance(processor, Worker_Inspect) and self.manager.logger:
                self.manager.logger.log_event(
                    "Processing", f"Completed processing job {job.id_job} by {processor.name_worker}")

        # Add to completed jobs list
        self.manager.completed_jobs.append(job)

        # Send job to next process
        self.send_job_to_next(job)

        # 자원이 해제되면 약간의 지연 후 새로운 자원 할당 시도
        self.env.process(self.check_resources_after_release())

    def check_resources_after_release(self):
        """자원 해제 후 약간의 지연을 두고 자원 할당 체크"""
        # 이벤트 처리 순서 충돌 방지를 위한 최소 지연
        yield self.env.timeout(0.0001)
        self.seize_resources()

    def send_job_to_next(self, job):
        """Send job to the next process - to be implemented by subclasses"""
        pass


# Subclass process implementations
class Proc_Build(Process):
    def __init__(self, env, manager):
        super().__init__("Proc_Build", env, manager)

        # Initialize 3D printing machines - ID를 1부터 시작
        for i in range(NUM_MACHINES_BUILD):
            self.list_processors.append(Mach_3DPrint(i+1))

    def send_job_to_next(self, job):
        """Send job to Wash process"""
        if self.manager.logger:
            self.manager.logger.log_event(
                "Process Flow", f"Moving job {job.id_job} from Build to Wash")
        self.manager.send_job_to_Proc_Wash(job)


class Proc_Wash(Process):
    def __init__(self, env, manager):
        super().__init__("Proc_Wash", env, manager)

        # Initialize wash machines - ID를 1부터 시작
        for i in range(NUM_MACHINES_WASH):
            self.list_processors.append(Mach_Wash(i+1))

    def send_job_to_next(self, job):
        """Send job to Dry process"""
        if self.manager.logger:
            self.manager.logger.log_event(
                "Process Flow", f"Moving job {job.id_job} from Wash to Dry")
        self.manager.send_job_to_Proc_Dry(job)


class Proc_Dry(Process):
    def __init__(self, env, manager):
        super().__init__("Proc_Dry", env, manager)

        # Initialize dry machines - ID를 1부터 시작
        for i in range(NUM_MACHINES_DRY):
            self.list_processors.append(Mach_Dry(i+1))

    def send_job_to_next(self, job):
        """Send job to Inspect process"""
        if self.manager.logger:
            self.manager.logger.log_event(
                "Process Flow", f"Moving job {job.id_job} from Dry to Inspect")
        self.manager.send_job_to_Proc_Inspect(job)


class Proc_Inspect(Process):
    def __init__(self, env, manager):
        super().__init__("Proc_Inspect", env, manager)

        # Initialize inspection workers - ID를 1부터 시작
        for i in range(NUM_WORKERS_IN_INSPECT):
            self.list_processors.append(Worker_Inspect(i+1))

    def send_job_to_next(self, job):
        """Complete the job after inspection (no next process)"""
        if self.manager.logger:
            self.manager.logger.log_event(
                "Process Flow", f"Completed job {job.id_job} after inspection")

        # Check if this completes any orders
        for order in self.manager.orders:
            self.manager.check_order_completion(order)
