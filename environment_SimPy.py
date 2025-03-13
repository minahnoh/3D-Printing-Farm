from config_SimPy import *
from environment_Customer import OrderReceiver
from environment_Process import Job, Proc_Build, Proc_Wash, Proc_Dry, Proc_Inspect
from environment_Processor import Worker, Machine


class Manager(OrderReceiver):
    def __init__(self, env):
        self.env = env
        self.logger = None  # Will be set by Logger
        self.defective_items_buffer = []

        # Initialize job counter
        self.job_counter = 1

        # Initialize processes
        self.proc_build = Proc_Build(env, self)
        self.proc_wash = Proc_Wash(env, self)
        self.proc_dry = Proc_Dry(env, self)
        self.proc_inspect = Proc_Inspect(env, self)

        # Statistics
        self.orders = []
        self.completed_orders = []
        self.completed_jobs = []
        self.defective_items = []

    def get_next_job_id(self):
        """Get next job ID and increment counter"""
        job_id = self.job_counter
        self.job_counter += 1
        return job_id

    def receive_order(self, order):
        """Implement OrderReceiver interface - receive order from Customer"""
        if self.logger:
            self.logger.log_event(
                "Order", f"Manager received Order {order.id_order} (Patients: {order.num_patients}, Total items: {sum(len(patient.list_items) for patient in order.list_patients)})")
        self.create_job_for_Proc_Build(order)

    def create_job_for_Proc_Build(self, order):
        """Create jobs from an order based on policy"""
        # Set the order start time
        order.time_start = self.env.now

        # Add order to tracking list
        self.orders.append(order)

        # Process each patient
        for patient in order.list_patients:
            # Group items by pallet size limit based on policy
            items = patient.list_items
            num_items = len(items)

            if self.logger:
                self.logger.log_event(
                    "Job Creation", f"Creating jobs for Patient {patient.id_patient} with {num_items} items")

            if num_items <= PALLET_SIZE_LIMIT:
                # Create one job for all items
                job = Job(self.get_next_job_id(), items)
                if self.logger:
                    self.logger.log_event(
                        "Job Creation", f"Created Job {job.id_job} with {len(job.list_items)} items")
                # Send job to build process
                self.send_job_to_Proc_Build(job)
            else:
                # Split based on policy
                if POLICY_ORDER_TO_JOB == "EQUAL_SPLIT":
                    # Calculate number of jobs needed
                    num_jobs = (num_items + PALLET_SIZE_LIMIT -
                                1) // PALLET_SIZE_LIMIT
                    items_per_job = num_items // num_jobs

                    if self.logger:
                        self.logger.log_event(
                            "Job Split", f"Splitting {num_items} items into {num_jobs} jobs")

                    # Create jobs with equal items
                    for i in range(num_jobs):
                        start_idx = i * items_per_job
                        end_idx = start_idx + items_per_job if i < num_jobs - 1 else num_items
                        job_items = items[start_idx:end_idx]
                        job = Job(self.get_next_job_id(), job_items)
                        if self.logger:
                            self.logger.log_event(
                                "Job Creation", f"Created Job {job.id_job} with {len(job.list_items)} items (split {i+1}/{num_jobs})")
                        # Send job to build process
                        self.send_job_to_Proc_Build(job)

                elif POLICY_ORDER_TO_JOB == "MAX_PACK":
                    # Pack as many as possible in each job
                    for i in range(0, num_items, PALLET_SIZE_LIMIT):
                        job_items = items[i:min(
                            i + PALLET_SIZE_LIMIT, num_items)]
                        job = Job(self.get_next_job_id(), job_items)
                        if self.logger:
                            self.logger.log_event(
                                "Job Creation", f"Created Job {job.id_job} with {len(job.list_items)} items (max pack)")
                        # Send job to build process
                        self.send_job_to_Proc_Build(job)

    def send_job_to_Proc_Build(self, job):
        """Send job to Build process"""
        if self.logger:
            self.logger.log_event(
                "Process Flow", f"Sending Job {job.id_job} to Build process")
        self.proc_build.add_to_queue(job)

    def send_job_to_Proc_Wash(self, job):
        """Send job to Wash process"""
        if self.logger:
            self.logger.log_event(
                "Process Flow", f"Sending Job {job.id_job} to Wash process")
        self.proc_wash.add_to_queue(job)

    def send_job_to_Proc_Dry(self, job):
        """Send job to Dry process"""
        if self.logger:
            self.logger.log_event(
                "Process Flow", f"Sending Job {job.id_job} to Dry process")
        self.proc_dry.add_to_queue(job)

    def send_job_to_Proc_Inspect(self, job):
        """Send job to Inspect process"""
        if self.logger:
            self.logger.log_event(
                "Process Flow", f"Sending Job {job.id_job} to Inspect process")
        self.proc_inspect.add_to_queue(job)

    def process_defective_items(self, defective_items):
        """Process defective items found in inspection"""
        # Add to buffer
        self.defective_items_buffer.extend(defective_items)
        self.defective_items.extend(defective_items)

        if self.logger:
            self.logger.log_event(
                "Defects", f"Added {len(defective_items)} defective items to buffer. Total in buffer: {len(self.defective_items_buffer)}")

        # Check if we have enough defective items to create a job
        if len(self.defective_items_buffer) >= POLICY_NUM_DEFECT_PER_JOB:
            if self.logger:
                self.logger.log_event(
                    "Defects", f"Creating reprocess job from {POLICY_NUM_DEFECT_PER_JOB} defective items")
            self.create_job_for_defects()

    def create_job_for_defects(self):
        """Create a job for defective items"""
        # Take the first N defective items from buffer
        items_for_job = self.defective_items_buffer[:POLICY_NUM_DEFECT_PER_JOB]
        self.defective_items_buffer = self.defective_items_buffer[POLICY_NUM_DEFECT_PER_JOB:]

        # Create new job for these items
        job = Job(self.get_next_job_id(), items_for_job)
        job.is_reprocess = True

        if self.logger:
            self.logger.log_event(
                "Reprocess", f"Created reprocess Job {job.id_job} with {len(items_for_job)} defective items")

        # Add to build queue based on policy
        if POLICY_REPROC_SEQ_IN_QUEUE == "QUEUE_LAST":
            self.proc_build.queue.append(job)
            if self.logger:
                self.logger.log_event(
                    "Queue Policy", f"Added reprocess Job {job.id_job} to end of Build queue")
            # Record queue length change
            self.proc_build.queue_length_history.append(
                (self.env.now, len(self.proc_build.queue)))
        elif POLICY_REPROC_SEQ_IN_QUEUE == "QUEUE_FIRST":
            self.proc_build.queue.insert(0, job)
            if self.logger:
                self.logger.log_event(
                    "Queue Policy", f"Added reprocess Job {job.id_job} to start of Build queue")
            # Record queue length change
            self.proc_build.queue_length_history.append(
                (self.env.now, len(self.proc_build.queue)))
        # More policies can be added here

    def check_order_completion(self, order):
        """Check if an order is completed and record statistics"""
        if order.check_completion() and order not in self.completed_orders:
            order.time_end = self.env.now
            self.completed_orders.append(order)
            if self.logger:
                makespan = order.time_end - order.time_start
                days = makespan / (24 * 60)
                self.logger.log_event(
                    "Order Completion", f"Order {order.id_order} completed with makespan of {days:.2f} days")
