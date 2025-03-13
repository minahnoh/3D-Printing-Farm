"""
main_SimPy.py
시뮬레이션을 실행하는 메인 파일
"""

import simpy
import random
from config_SimPy import *
from environment_SimPy import *
from log_SimPy import sim_logger


def run_simulation(seed=0):
    random.seed(seed)
    env = simpy.Environment()

    # Process 객체 생성
    proc_build = Proc_Build(env, "Build", manager=None)
    proc_wash = Proc_Wash(env, "Wash", manager=None)
    proc_dry = Proc_Dry(env, "Dry", manager=None)
    proc_inspect = Proc_Inspect(env, "Inspect", manager=None)

    # Manager 생성
    manager = Manager(env, proc_build, proc_wash, proc_dry, proc_inspect)
    # 각 proc에 manager 연결
    proc_build.manager = manager
    proc_wash.manager = manager
    proc_dry.manager = manager
    proc_inspect.manager = manager

    # Machine/Worker 생성 (config에 설정된 수만큼)
    # Build 공정
    for i in range(NUM_MACHINES_BUILD):
        m = Mach_3DPrint(env, id_machine=i+1, id_process="Build",
                         name_machine=f"3DPrint_{i+1}",
                         processing_time=BUILD_MACHINE_TIME_HOURS,
                         capacity_jobs=NUM_MACHINES_BUILD)
        proc_build.list_processors.append(m)

    # Wash 공정
    for i in range(NUM_MACHINES_WASH):
        w = Mach_Wash(env, id_machine=i+1, id_process="Wash",
                      name_machine=f"Wash_{i+1}",
                      processing_time=WASH_MACHINE_TIME_HOURS,
                      capacity_jobs=NUM_MACHINES_WASH)
        proc_wash.list_processors.append(w)

    # Dry 공정
    for i in range(NUM_MACHINES_DRY):
        d = Mach_Dry(env, id_machine=i+1, id_process="Dry",
                     name_machine=f"Dry_{i+1}",
                     processing_time=DRY_MACHINE_TIME_HOURS,
                     capacity_jobs=NUM_MACHINES_DRY)
        proc_dry.list_processors.append(d)

    # Inspect 공정(Worker)
    for i in range(NUM_WORKERS_IN_INSPECT):
        wi = Worker_Inspect(env, id_worker=i+1, name_worker=f"Inspector_{i+1}",
                            processing_time=INSPECT_WORKER_TIME_HOURS)
        proc_inspect.list_processors.append(wi)

    # Customer 생성
    customer = Customer(env, manager,
                        order_cycle_hours=CUST_ORDER_CYCLE * 24)
    env.process(customer.run())

    # # Queue 길이 모니터링 예시(선택)
    # def monitor_queues(env, processes):
    #     while True:
    #         for p in processes:
    #             sim_logger.log_queue_length(p.name, env.now, len(p.queue))
    #         yield env.timeout(1.0)

    # env.process(monitor_queues(
    #     env, [proc_build, proc_wash, proc_dry, proc_inspect]))

    # 시뮬레이션 실행
    env.run(until=SIM_TIME * 24)

    # -----------------------
    # 시뮬레이션 종료 후 결과
    # -----------------------
    # 1) 이벤트 로그 출력(일 단위)
    if FLAG_PRINT_EVENT_LOG:
        sim_logger.print_event_logs_by_day()

    # 2) 평균 makespan 계산 (Manager 안의 completed_orders)
    if manager.completed_orders:
        total = 0
        for od in manager.completed_orders:
            total += (od.time_end - od.time_start)
        avg_makespan_hours = total / len(manager.completed_orders)
        avg_makespan_days = avg_makespan_hours / 24.0  # 일 단위 변환

        print(f"\n=== 평균 makespan ===")
        print(f"완료된 {len(manager.completed_orders)}개 Order 기준:")
        print(f" - {avg_makespan_hours:.2f} hrs")
        print(f" - {avg_makespan_days:.2f} days")

    else:
        print("\n완료된 Order가 없습니다. (시뮬레이션 시간이 짧거나 다른 이유)")

    # 기타 통계, 간트차트 등
    sim_logger.summarize_results()
    if FLAG_SHOW_PLOTLY:
        fig = sim_logger.create_gantt_chart()
        if fig:
            fig.show()


if __name__ == "__main__":
    run_simulation(seed=42)
