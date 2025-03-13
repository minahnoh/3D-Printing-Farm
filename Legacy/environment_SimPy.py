"""
environment_SimPy.py
- Customer, Order, Patient, Item
- Manager
- Process (및 하위: Proc_Build, Proc_Wash, Proc_Dry, Proc_Inspect)
- Machine (하위: Mach_3DPrint, Mach_Wash, Mach_Dry)
- Worker (하위: Worker_Inspect)
- Job
"""

import simpy
import random
import itertools

from config_SimPy import *
from log_SimPy import sim_logger


#####################################################################
# 1. 고객 및 주문 관련 클래스
#####################################################################

class Customer:
    def __init__(self, env, manager, order_cycle_hours):
        self.env = env
        self.manager = manager
        self.order_cycle_hours = order_cycle_hours
        self.order_counter = 0

    def _create_order(self):
        self.order_counter += 1
        # 주문 생성
        new_order = Order(self.env, self.order_counter)
        # 로그 기록
        if FLAG_PRINT_EVENT_LOG:
            sim_logger.log_event(
                time=self.env.now,
                message=f"[Customer] Order #{self.order_counter} created."
            )
        # manager에 전달
        self.manager.receive_order(new_order)

    def run(self):
        # 시작하자마자 첫 주문 생성
        self._create_order()
        while True:
            # 주기적으로 order 생성
            yield self.env.timeout(self.order_cycle_hours)
            self._create_order()


class Order:
    """
    Order
    - 여러 Patient를 보유
    - 전체 생산 완료 시점(time_end)을 기록해두어 makespan 계산
    """

    def __init__(self, env, id_order):
        self.env = env
        self.id_order = id_order
        self.num_patients = NUM_PATIENTS_PER_ORDER()
        self.list_patients = []
        self.due_date = CUST_ORDER_DUE * 24
        self.time_start = env.now
        self.time_end = None  # 생산이 완료되었을 때 기록

        self._create_patients()

    def _create_patients(self):
        for i in range(self.num_patients):
            p = Patient(self.env, self.id_order, i + 1)
            self.list_patients.append(p)

    @property
    def is_completed(self):
        """Order가 완전히 완료되었는지(모든 patient가 완료되었는지)"""
        return all(patient.is_completed for patient in self.list_patients)


class Patient:
    def __init__(self, env, id_order, id_patient):
        self.env = env
        self.id_order = id_order
        self.id_patient = id_patient

        self.num_items = NUM_ITEMS_PER_PATIENT()
        self.list_items = []
        self.is_completed = False

        self._create_items()

    def _create_items(self):
        for i in range(self.num_items):
            item_obj = Item(
                self.env,
                id_order=self.id_order,
                id_patient=self.id_patient,
                id_item=i + 1,
                parent_patient=self
            )
            self.list_items.append(item_obj)

    def check_completed(self):
        """모든 Item의 is_completed가 True면, Patient를 완료 상태로."""
        if all(item.is_completed for item in self.list_items):
            self.is_completed = True


class Item:
    def __init__(self, env, id_order, id_patient, id_item, parent_patient=None):
        self.env = env
        self.id_order = id_order
        self.id_patient = id_patient
        self.id_item = id_item

        self.parent_patient = parent_patient

        self.type_item = "aligner"
        self.is_completed = False
        self.is_defect = False


#####################################################################
# 2. Job 및 Manager 클래스
#####################################################################

class Job:
    _job_id_counter = itertools.count(1)

    def __init__(self, env, list_items):
        self.env = env
        self.id_job = next(Job._job_id_counter)
        self.workstation = None
        self.list_items = list_items

        self.time_processing_start = None
        self.time_processing_end = None
        self.time_waiting_start = None
        self.time_waiting_end = None


class Manager:
    def __init__(self, env, proc_build, proc_wash, proc_dry, proc_inspect):
        self.env = env
        self.proc_build = proc_build
        self.proc_wash = proc_wash
        self.proc_dry = proc_dry
        self.proc_inspect = proc_inspect

        self.defect_buffer = []
        self.active_orders = []
        self.completed_orders = []  # 완료된 order 리스트

    def receive_order(self, order):
        """Order를 받아서 Job으로 나눈 뒤 Build 공정 queue에 넣음."""
        self.active_orders.append(order)
        jobs = self.create_job_for_Proc_Build(order)
        self.send_job_to_Proc_Build(jobs)

    def create_job_for_Proc_Build(self, order):
        jobs_to_send = []
        for patient_obj in order.list_patients:
            num_items = patient_obj.num_items

            if num_items <= PALLET_SIZE_LIMIT:
                # 1개의 Job
                job = Job(self.env, patient_obj.list_items)
                jobs_to_send.append(job)
            else:
                # PALLET_SIZE_LIMIT를 초과 -> POLICY_ORDER_TO_JOB 확인
                if POLICY_ORDER_TO_JOB == "EQUAL_SPLIT":
                    n_splits = (num_items - 1) // PALLET_SIZE_LIMIT + 1
                    items_per_split = num_items // n_splits

                    start_idx = 0
                    for split_idx in range(n_splits):
                        if split_idx < n_splits - 1:
                            part_items = patient_obj.list_items[start_idx: start_idx+items_per_split]
                            start_idx += items_per_split
                        else:
                            part_items = patient_obj.list_items[start_idx:]
                        job = Job(self.env, part_items)
                        jobs_to_send.append(job)

                elif POLICY_ORDER_TO_JOB == "MAX_PACK":
                    start_idx = 0
                    while start_idx < num_items:
                        part_items = patient_obj.list_items[start_idx: start_idx +
                                                            PALLET_SIZE_LIMIT]
                        job = Job(self.env, part_items)
                        jobs_to_send.append(job)
                        start_idx += PALLET_SIZE_LIMIT
                else:
                    # 기본은 그냥 한 Job
                    job = Job(self.env, patient_obj.list_items)
                    jobs_to_send.append(job)

        return jobs_to_send

    def send_job_to_Proc_Build(self, jobs):
        for job in jobs:
            self.proc_build.queue.append(job)
            if FLAG_PRINT_EVENT_LOG:
                sim_logger.log_event(
                    time=self.env.now,
                    message=f"[Manager] Job #{job.id_job} -> Proc_Build.queue"
                )

    def send_job_to_Proc_Wash(self, job):
        self.proc_wash.queue.append(job)
        if FLAG_PRINT_EVENT_LOG:
            sim_logger.log_event(
                time=self.env.now,
                message=f"[Manager] Job #{job.id_job} -> Proc_Wash.queue"
            )

    def send_job_to_Proc_Dry(self, job):
        self.proc_dry.queue.append(job)
        if FLAG_PRINT_EVENT_LOG:
            sim_logger.log_event(
                time=self.env.now,
                message=f"[Manager] Job #{job.id_job} -> Proc_Dry.queue"
            )

    def send_job_to_Proc_Inspect(self, job):
        self.proc_inspect.queue.append(job)
        if FLAG_PRINT_EVENT_LOG:
            sim_logger.log_event(
                time=self.env.now,
                message=f"[Manager] Job #{job.id_job} -> Proc_Inspect.queue"
            )

    def create_job_for_defects(self, list_defect_items):
        """불량 아이템을 모아서 재작업 Job 생성 -> Proc_Build queue에 삽입"""
        self.defect_buffer.extend(list_defect_items)

        while len(self.defect_buffer) >= POLICY_NUM_DEFECT_PER_JOB:
            defect_items = self.defect_buffer[:POLICY_NUM_DEFECT_PER_JOB]
            self.defect_buffer = self.defect_buffer[POLICY_NUM_DEFECT_PER_JOB:]
            rework_job = Job(self.env, defect_items)

            if POLICY_REPROC_SEQ_IN_QUEUE == "QUEUE_LAST":
                self.proc_build.queue.append(rework_job)
            else:
                self.proc_build.queue.insert(0, rework_job)

            if FLAG_PRINT_EVENT_LOG:
                sim_logger.log_event(
                    time=self.env.now,
                    message=f"[Manager] Rework Job #{rework_job.id_job} with {len(defect_items)} defect items -> Proc_Build.queue"
                )

    def check_order_completion(self):
        """
        모든 Order에 대해, 완성되었으면 time_end 설정 후
        completed_orders로 이동. (중복처리 방지를 위해)
        """
        for order in list(self.active_orders):
            if order.is_completed:
                if order.time_end is None:
                    order.time_end = self.env.now
                    self.completed_orders.append(order)
                    self.active_orders.remove(order)
                    if FLAG_PRINT_EVENT_LOG:
                        sim_logger.log_event(
                            time=self.env.now,
                            message=f"[Manager] Order #{order.id_order} completed. Makespan={order.time_end - order.time_start:.2f}"
                        )


#####################################################################
# 3. Process (Build, Wash, Dry, Inspect)
#####################################################################

class Process:
    def __init__(self, env, name, manager):
        self.env = env
        self.name = name
        self.manager = manager

        self.queue = []
        self.list_processors = []
        self.policy_dispatch_from_queue = POLICY_DISPATCH_FROM_QUEUE

        self.action = env.process(self.run())

    def run(self):
        while True:
            if len(self.queue) > 0 and self._has_available_processor():
                # 큐에서 job 꺼내기
                job = self._dispatch_job_from_queue()
                processor = self._get_available_processor()

                yield self.env.process(self.seize_resources(job, processor))

            else:
                yield self.env.timeout(0.1)

    def seize_resources(self, job, processor):
        # 시간 기록
        job.time_waiting_end = self.env.now
        job.time_processing_start = self.env.now

        # processor에 job 할당
        if processor.type_processor == "Machine":
            job.workstation = {"type": "Machine", "id": processor.id_machine}
        elif processor.type_processor == "Worker":
            job.workstation = {"type": "Worker", "id": processor.id_worker}

        processor.list_working_jobs.append(job)
        processor.available_status = False

        if FLAG_PRINT_EVENT_LOG:
            sim_logger.log_event(
                time=self.env.now,
                message=f"[{self.name}] Seize Job #{job.id_job} -> Processor={job.workstation}"
            )

        # delay_job
        self.delay_job(job, processor)

    def delay_job(self, job, processor):
        # 여기서 디버그 용으로 찍어보기
        print(f"[DEBUG] Job #{job.id_job}: "
              f"queue_in={job.time_waiting_start}, queue_out={job.time_waiting_end}, "
              f"start={job.time_processing_start}, end={job.time_processing_end}, workstation={job.workstation}")

        yield self.env.process(processor.process_machine(job))
        job.time_processing_end = self.env.now

        # release_job
        self.release_job(job, processor)

    def release_job(self, job, processor):
        # 여기서 디버그 용으로 찍어보기
        print(f"[DEBUG] Job #{job.id_job}: "
              f"queue_in={job.time_waiting_start}, queue_out={job.time_waiting_end}, "
              f"start={job.time_processing_start}, end={job.time_processing_end}, workstation={job.workstation}")

        job.workstation = None
        processor.list_working_jobs.remove(job)
        processor.available_status = True

        if FLAG_PRINT_EVENT_LOG:
            sim_logger.log_event(
                time=self.env.now,
                message=f"[{self.name}] Release Job #{job.id_job}"
            )

        sim_logger.log_job(
            job=job,
            process_name=self.name,
            machine_name=(processor.name_machine if hasattr(
                processor, 'name_machine') else processor.name_worker),
            t_queue_in=(job.time_waiting_start or 0),  # 큐에 들어온 시점
            t_queue_out=job.time_waiting_end,
            t_start=job.time_processing_start,
            t_end=job.time_processing_end
        )

        # 여기서 디버그 용으로 찍어보기
        print(f"[DEBUG] Job #{job.id_job}: "
              f"queue_in={job.time_waiting_start}, queue_out={job.time_waiting_end}, "
              f"start={job.time_processing_start}, end={job.time_processing_end}, workstation={job.workstation}")

        self.send_job_to_next(job)

    def send_job_to_next(self, job):
        """다음 공정으로 Job 보내기 (하위 클래스에서 구현)"""
        pass

    def _dispatch_job_from_queue(self):
        if self.policy_dispatch_from_queue == "FIFO":
            job = self.queue.pop(0)
        else:
            job = self.queue.pop()  # LIFO 등
        if job.time_waiting_start is None:
            job.time_waiting_start = self.env.now
        return job

    def _has_available_processor(self):
        return any(proc.available_status for proc in self.list_processors)

    def _get_available_processor(self):
        for proc in self.list_processors:
            if proc.available_status:
                return proc
        return None


class Proc_Build(Process):
    def send_job_to_next(self, job):
        # 불량 여부 확률적으로 결정
        for item in job.list_items:
            if random.random() < DEFECT_RATE_PROC_BUILD:
                item.is_defect = True
        self.manager.send_job_to_Proc_Wash(job)


class Proc_Wash(Process):
    def send_job_to_next(self, job):
        self.manager.send_job_to_Proc_Dry(job)


class Proc_Dry(Process):
    def send_job_to_next(self, job):
        self.manager.send_job_to_Proc_Inspect(job)


class Proc_Inspect(Process):
    def send_job_to_next(self, job):
        # 불량품 있으면 재작업 Job 생성
        defect_items = [it for it in job.list_items if it.is_defect]
        if defect_items:
            self.manager.create_job_for_defects(defect_items)

        # 각 아이템이 속한 Patient를 체크해 완료 여부 갱신
        for it in job.list_items:
            it.is_completed = True
            # 아이템이 속한 Patient가 있는 경우
            if it.parent_patient is not None:
                it.parent_patient.check_completed()

        # 매번 job 처리 후 order 완료여부 체크
        self.manager.check_order_completion()


#####################################################################
# 4. Machine/Worker 클래스
#####################################################################

class Machine:
    def __init__(self, env, id_machine, id_process, name_machine, processing_time, capacity_jobs):
        self.env = env
        self.type_processor = "Machine"
        self.id_machine = id_machine
        self.id_process = id_process
        self.name_machine = name_machine

        self.available_status = True
        self.list_working_jobs = []  # <--- Worker도 동일하게 맞춤
        self.capacity_jobs = capacity_jobs
        self.processing_time = processing_time

    def process_machine(self, job):
        yield self.env.timeout(self.processing_time)


class Mach_3DPrint(Machine):
    pass


class Mach_Wash(Machine):
    pass


class Mach_Dry(Machine):
    pass


class Worker:
    def __init__(self, env, id_worker, name_worker, processing_time):
        self.env = env
        self.type_processor = "Worker"
        self.id_worker = id_worker
        self.name_worker = name_worker

        self.available_status = True
        self.list_working_jobs = []
        self.capacity_jobs = 1
        self.processing_time = processing_time

    def process_machine(self, job):
        yield self.env.timeout(self.processing_time)


class Worker_Inspect(Worker):
    pass
