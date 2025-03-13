# log_SimPy.py
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from environment_SimPy import Machine, Worker
from config_SimPy import *


class Logger:
    def __init__(self, manager):
        self.manager = manager
        self.env = manager.env
        # Set logger in manager
        manager.logger = self

    def log_event(self, event_type, message):
        """ Log an event with a timestamp """
        if EVENT_LOGGING:
            current_time = self.env.now
            days = int(current_time // (24 * 60))
            hours = int((current_time % (24 * 60)) // 60)
            minutes = int(current_time % 60)
            timestamp = f"{days:02d}:{hours:02d}:{minutes:02d}"
            total_minutes = int(current_time)
            print(f"[{timestamp}] [{total_minutes}] | {event_type}: {message}")

    def collect_statistics(self):
        """Collect statistics from the simulation"""
        stats = {}

        # Order statistics
        if self.manager.completed_orders:
            order_makespans = [(order.time_end - order.time_start)
                               for order in self.manager.completed_orders]
            stats['order_makespan_avg'] = sum(
                order_makespans) / len(order_makespans)
            stats['order_makespan_std'] = np.std(
                order_makespans) if len(order_makespans) > 1 else 0

        # Job waiting time and processing time statistics
        process_ids = ["Proc_Build", "Proc_Wash", "Proc_Dry", "Proc_Inspect"]
        process_jobs = {proc_id: [] for proc_id in process_ids}

        for job in self.manager.completed_jobs:
            process_id = job.workstation['Process']
            if process_id in process_ids:
                process_jobs[process_id].append(job)

        for process_id, jobs in process_jobs.items():
            if jobs:
                # Waiting time statistics
                waiting_times = [(job.time_waiting_end - job.time_waiting_start)
                                 for job in jobs
                                 if job.time_waiting_end is not None and job.time_waiting_start is not None]
                if waiting_times:
                    stats[f'{process_id}_waiting_time_avg'] = sum(
                        waiting_times) / len(waiting_times)
                    stats[f'{process_id}_waiting_time_std'] = np.std(
                        waiting_times) if len(waiting_times) > 1 else 0

                # Processing time statistics
                processing_times = [(job.time_processing_end - job.time_processing_start)
                                    for job in jobs
                                    if job.time_processing_end is not None and job.time_processing_start is not None]
                if processing_times:
                    stats[f'{process_id}_processing_time_avg'] = sum(
                        processing_times) / len(processing_times)
                    stats[f'{process_id}_processing_time_std'] = np.std(
                        processing_times) if len(processing_times) > 1 else 0

                # System time (waiting + processing time) statistics
                system_times = [(job.time_processing_end - job.time_waiting_start)
                                for job in jobs
                                if job.time_processing_end is not None and job.time_waiting_start is not None]
                if system_times:
                    stats[f'{process_id}_system_time_avg'] = sum(
                        system_times) / len(system_times)
                    stats[f'{process_id}_system_time_std'] = np.std(
                        system_times) if len(system_times) > 1 else 0

        # Queue length statistics
        for process in [self.manager.proc_build, self.manager.proc_wash, self.manager.proc_dry, self.manager.proc_inspect]:
            if process.queue_length_history:
                # Calculate time-weighted average queue length
                times = [t for t, _ in process.queue_length_history]
                lengths = [l for _, l in process.queue_length_history]

                # Add final time point if missing
                if times[-1] < self.env.now:
                    times.append(self.env.now)
                    lengths.append(lengths[-1])

                # Calculate time-weighted average
                weighted_sum = 0
                for i in range(1, len(times)):
                    weighted_sum += lengths[i-1] * (times[i] - times[i-1])

                avg_length = weighted_sum / self.env.now if self.env.now > 0 else 0
                stats[f'{process.id_process}_avg_queue_length'] = avg_length

                # Calculate standard deviation of queue length
                if len(lengths) > 1:
                    stats[f'{process.id_process}_queue_length_std'] = np.std(
                        lengths)
                else:
                    stats[f'{process.id_process}_queue_length_std'] = 0

        # Machine and worker utilization statistics
        for process in [self.manager.proc_build, self.manager.proc_wash, self.manager.proc_dry, self.manager.proc_inspect]:
            process_utilization = []
            for processor in process.list_processors:
                # Calculate utilization (busy time / total time)
                utilization = processor.busy_time / self.env.now if self.env.now > 0 else 0
                process_utilization.append(utilization)

                # Record individual processor utilization
                if isinstance(processor, Machine):
                    stats[f'{processor.name_machine}_utilization'] = utilization
                elif isinstance(processor, Worker):
                    stats[f'{processor.name_worker}_utilization'] = utilization

            # Calculate average utilization for this process
            if process_utilization:
                stats[f'{process.id_process}_avg_utilization'] = sum(
                    process_utilization) / len(process_utilization)

        # Defect statistics
        stats['total_defects'] = len(self.manager.defective_items)
        if stats['total_defects'] > 0 and self.manager.completed_jobs:
            total_items = sum(len(job.list_items)
                              for job in self.manager.completed_jobs)
            stats['defect_rate'] = stats['total_defects'] / \
                total_items if total_items > 0 else 0

        return stats

    def get_all_resources(self):
        """각 머신의 capacity에 따라 슬롯으로 분할된 자원 목록 생성"""
        resources = []

        # Build 프로세스의 머신들을 슬롯으로 분할
        for machine in self.manager.proc_build.list_processors:
            if machine.capacity_jobs > 1:
                # 용량이 1보다 크면 슬롯으로 분할
                for slot in range(machine.capacity_jobs):
                    resources.append({
                        'name': f"{machine.name_machine}_Slot{slot+1}",
                        'original_name': machine.name_machine,
                        'slot': slot,
                        'type': 'Machine',
                        'process': 'Proc_Build'
                    })
            else:
                # 용량이 1이면 그대로 추가
                resources.append({
                    'name': machine.name_machine,
                    'original_name': machine.name_machine,
                    'slot': 0,
                    'type': 'Machine',
                    'process': 'Proc_Build'
                })

        # Wash 프로세스의 머신들을 슬롯으로 분할
        for machine in self.manager.proc_wash.list_processors:
            if machine.capacity_jobs > 1:
                for slot in range(machine.capacity_jobs):
                    resources.append({
                        'name': f"{machine.name_machine}_Slot{slot+1}",
                        'original_name': machine.name_machine,
                        'slot': slot,
                        'type': 'Machine',
                        'process': 'Proc_Wash'
                    })
            else:
                resources.append({
                    'name': machine.name_machine,
                    'original_name': machine.name_machine,
                    'slot': 0,
                    'type': 'Machine',
                    'process': 'Proc_Wash'
                })

        # Dry 프로세스의 머신들을 슬롯으로 분할
        for machine in self.manager.proc_dry.list_processors:
            if machine.capacity_jobs > 1:
                for slot in range(machine.capacity_jobs):
                    resources.append({
                        'name': f"{machine.name_machine}_Slot{slot+1}",
                        'original_name': machine.name_machine,
                        'slot': slot,
                        'type': 'Machine',
                        'process': 'Proc_Dry'
                    })
            else:
                resources.append({
                    'name': machine.name_machine,
                    'original_name': machine.name_machine,
                    'slot': 0,
                    'type': 'Machine',
                    'process': 'Proc_Dry'
                })

        # Inspect 프로세스의 작업자들은 capacity가 1이므로 그대로 추가
        for worker in self.manager.proc_inspect.list_processors:
            resources.append({
                'name': worker.name_worker,
                'original_name': worker.name_worker,
                'slot': 0,
                'type': 'Worker',
                'process': 'Proc_Inspect'
            })

        return resources

    def get_color_for_job(self, job_id):
        """Return a color based on the job ID"""
        # List of colors for jobs - using a colorful palette
        colors = [
            'rgba(31, 119, 180, 0.8)',   # Blue
            'rgba(255, 127, 14, 0.8)',   # Orange
            'rgba(44, 160, 44, 0.8)',    # Green
            'rgba(214, 39, 40, 0.8)',    # Red
            'rgba(148, 103, 189, 0.8)',  # Purple
            'rgba(140, 86, 75, 0.8)',    # Brown
            'rgba(227, 119, 194, 0.8)',  # Pink
            'rgba(127, 127, 127, 0.8)',  # Gray
            'rgba(188, 189, 34, 0.8)',   # Olive
            'rgba(23, 190, 207, 0.8)'    # Cyan
        ]

        # Use modulo to cycle through colors for large number of jobs
        return colors[job_id % len(colors)]

    def visualize_gantt(self):
        """슬롯 기반 Gantt 차트 생성 - 작업별 슬롯 일관성 유지"""
        if not GANTT_CHART_ENABLED:
            return None

        # Get all resources with slots
        all_resources = self.get_all_resources()
        resource_names = [r['name'] for r in all_resources]

        # 리소스 이름과 원본 이름 매핑 생성
        resource_mapping = {r['name']: r['original_name']
                            for r in all_resources}

        # 원본 이름과 슬롯 인덱스 매핑
        slot_mapping = {}
        for r in all_resources:
            if r['original_name'] not in slot_mapping:
                slot_mapping[r['original_name']] = []
            slot_mapping[r['original_name']].append((r['name'], r['slot']))

        # Create a trace for each job's processing step
        fig = go.Figure()

        # Track which resources have jobs
        resources_with_jobs = set()

        # Create dict to track created traces by job ID
        trace_keys = {}

        # 작업 할당 상태 추적
        slot_assignment = {name: [] for name in resource_names}

        # 중요: 작업-머신별 슬롯 할당 기록 추적 (작업별 슬롯 일관성 유지)
        job_machine_slot = {}  # {(job_id, machine_name): assigned_slot_name}

        for job in self.manager.completed_jobs:
            # Job ID
            job_id = job.id_job

            # Check if job has processing history
            if hasattr(job, 'processing_history') and job.processing_history:
                # Get a consistent color for this job
                job_color = self.get_color_for_job(job_id)

                for step in job.processing_history:
                    # Skip incomplete steps
                    if step['end_time'] is None:
                        continue

                    # Get original resource name
                    orig_resource = step['resource_name']

                    # 머신일 경우 슬롯 할당
                    if step['resource_type'] == 'Machine' and orig_resource in slot_mapping:
                        # 작업의 시작/종료 시간
                        start_min = step['start_time']
                        end_min = step['end_time']
                        duration_min = end_min - start_min

                        # 시간이 유효한지 확인
                        if duration_min <= 0:
                            continue

                        # 작업-머신 할당 키 생성
                        job_machine_key = (job_id, orig_resource)

                        # 이 작업이 이전에 이 머신에 할당된 적이 있는지 확인
                        if job_machine_key in job_machine_slot:
                            # 이전에 할당된 슬롯 재사용
                            assigned_slot = job_machine_slot[job_machine_key]
                        else:
                            # 원본 머신의 모든 슬롯 정보
                            slots = slot_mapping[orig_resource]

                            # 적절한 슬롯 찾기 (겹치지 않는 슬롯)
                            assigned_slot = None
                            for slot_name, slot_index in slots:
                                # 이 슬롯에 할당된 기존 작업들 확인
                                conflict = False
                                for existing_start, existing_end, existing_job_id in slot_assignment[slot_name]:
                                    # 같은 작업이면 충돌로 보지 않음
                                    if existing_job_id == job_id:
                                        continue
                                    # 시간이 겹치는지 확인
                                    if not (end_min <= existing_start or start_min >= existing_end):
                                        conflict = True
                                        break

                                # 시간이 겹치지 않으면 이 슬롯에 할당
                                if not conflict:
                                    assigned_slot = slot_name
                                    # 작업-머신 슬롯 할당 기록
                                    job_machine_slot[job_machine_key] = assigned_slot
                                    break

                            # 적합한 슬롯을 찾지 못했다면 첫 번째 슬롯에 강제 할당
                            if assigned_slot is None:
                                assigned_slot = slots[0][0]
                                # 작업-머신 슬롯 할당 기록
                                job_machine_slot[job_machine_key] = assigned_slot

                        # 선택된 슬롯에 작업 기록 추가 (작업 ID도 함께 저장)
                        slot_assignment[assigned_slot].append(
                            (start_min, end_min, job_id))

                        # 선택된 슬롯에 작업 추가
                        resource_name = assigned_slot

                    else:
                        # Worker는 슬롯이 필요 없음
                        resource_name = orig_resource
                        start_min = step['start_time']
                        end_min = step['end_time']
                        duration_min = end_min - start_min

                        # 시간이 유효한지 확인
                        if duration_min <= 0:
                            continue

                    # Add to resources with jobs
                    resources_with_jobs.add(resource_name)

                    # Create trace name using only the job ID
                    trace_name = f"Job {job_id}"
                    trace_key = str(job_id)

                    # Check if we already created a legend entry for this job
                    show_legend = trace_key not in trace_keys
                    if show_legend:
                        trace_keys[trace_key] = True

                    # Create trace for this step
                    fig.add_trace(go.Bar(
                        y=[resource_name],
                        x=[duration_min],
                        base=start_min,
                        orientation='h',
                        name=trace_name,
                        marker_color=job_color,
                        text=f"Job {job_id}",
                        hovertext=f"Job {job_id} - {step['process']} - Duration: {duration_min} mins",
                        showlegend=show_legend,
                        legendgroup=trace_key,
                    ))

        # Add invisible traces for resources with no jobs
        for resource in resource_names:
            if resource not in resources_with_jobs:
                fig.add_trace(go.Bar(
                    y=[resource],
                    x=[0.001],
                    base=0,
                    orientation='h',
                    marker_color='rgba(0,0,0,0)',
                    showlegend=False,
                    hoverinfo="skip"
                ))

        # Customize layout
        fig.update_layout(
            title="Job Processing Gantt Chart",
            barmode='overlay',
            xaxis_title="Simulation Time (minutes)",
            yaxis_title="Resource",
            yaxis=dict(
                categoryorder='array',
                categoryarray=resource_names
            ),
            legend_title="Jobs",
            height=max(600, len(resource_names) * 30),
            showlegend=True
        )

        return fig

    def visualize_process_statistics(self, stats, stat_type):
        """Visualize process statistics (waiting time, processing time, system time)"""
        if not VIS_STAT_ENABLED:
            return None

        processes = ["Proc_Build", "Proc_Wash", "Proc_Dry", "Proc_Inspect"]

        # Extract relevant statistics
        avg_values = []
        std_values = []

        for process in processes:
            avg_key = f'{process}_{stat_type}_avg'
            std_key = f'{process}_{stat_type}_std'

            if avg_key in stats:
                avg_values.append(stats[avg_key])
                std_values.append(stats[std_key] if std_key in stats else 0)
            else:
                avg_values.append(0)
                std_values.append(0)

        # Create bar chart with error bars
        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=processes,
            y=avg_values,
            error_y=dict(
                type='data',
                array=std_values,
                visible=True
            ),
            name='Average'
        ))

        fig.update_layout(
            title=f"Process {stat_type.replace('_', ' ').title()}",
            xaxis_title="Process",
            yaxis_title=f"{stat_type.replace('_', ' ').title()} (minutes)"
        )

        return fig

    def visualize_statistics(self, stats):
        """Visualize various statistics"""
        figures = {}

        # Process timings visualization - only if VIS_STAT_ENABLED
        if VIS_STAT_ENABLED:
            figures['waiting_time'] = self.visualize_process_statistics(
                stats, 'waiting_time')
            figures['processing_time'] = self.visualize_process_statistics(
                stats, 'processing_time')
            figures['system_time'] = self.visualize_process_statistics(
                stats, 'system_time')

            # Resource utilization visualization
            figures['utilization'] = self.visualize_utilization(stats)

            # Queue length visualization
            figures['queue_length'] = self.visualize_queue_lengths()

        # Gantt chart (only if enabled) - independent of VIS_STAT_ENABLED
        if GANTT_CHART_ENABLED:
            figures['gantt'] = self.visualize_gantt()

        # Display all figures
        for name, fig in figures.items():
            if fig is not None:
                fig.show()

        return figures


def get_color_for_process(process_name):
    """Return a color based on the process name"""
    colors = {
        'Proc_Build': 'rgba(31, 119, 180, 0.8)',  # Blue
        'Proc_Wash': 'rgba(255, 127, 14, 0.8)',   # Orange
        'Proc_Dry': 'rgba(44, 160, 44, 0.8)',     # Green
        'Proc_Inspect': 'rgba(214, 39, 40, 0.8)'  # Red
    }
    # Purple default
    return colors.get(process_name, 'rgba(148, 103, 189, 0.8)')
