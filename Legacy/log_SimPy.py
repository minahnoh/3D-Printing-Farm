"""
log_SimPy.py
- 시뮬레이션 로그를 기록/시각화
"""

import pandas as pd
import plotly.express as px


class SimulationLogger:
    def __init__(self):
        self.event_logs = []       # 이벤트(시간, 메시지)
        self.records_jobs = []     # Job 단위 기록
        self.records_queue_length = []
        self.processor_records = []

    def _format_time_day_hour_min(self, t_in_hours: float) -> str:
        """
        SimPy 내부 시간(시간 단위)을 "DAY:HH:MM"로 변환해주는 헬퍼 함수
        """
        total_minutes = int(t_in_hours * 60)
        day = total_minutes // (24 * 60) + 1  # Day 1부터 시작
        leftover = total_minutes % (24 * 60)
        hour = leftover // 60
        minute = leftover % 60

        # 예: Day 0, 05:30
        return f"Day {day}, {hour:02d}:{minute:02d}"

    def log_event(self, time, message):
        """
        이벤트 발생 시점을 'DAY:HOUR:MIN' 형태로 기록
        """
        formatted_time = self._format_time_day_hour_min(time)
        self.event_logs.append({
            'time_hours': time,        # 원본 시간(시간 단위)
            'time_str': formatted_time,  # "DAY:HH:MM"
            'message': message
        })

    def print_event_logs_by_day(self):
        """
        event_logs를 시간 순으로 출력
        """
        if not self.event_logs:
            print("No event logs to display.")
            return

        self.event_logs.sort(key=lambda x: x['time_hours'])
        for ev in self.event_logs:
            print(f"{ev['time_str']} | {ev['message']}")

    def log_job(self, job, process_name, machine_name,
                t_queue_in, t_queue_out, t_start, t_end):
        self.records_jobs.append({
            'job_id': job.id_job,
            'process': process_name,
            'machine': machine_name,
            't_queue_in': t_queue_in,
            't_queue_out': t_queue_out,
            't_processing_start': t_start,
            't_processing_end': t_end
        })

    def log_queue_length(self, process_name, t, length):
        self.records_queue_length.append({
            'process': process_name,
            'time': t,
            'queue_length': length
        })

    def log_processor_status(self, processor_name, utilization):
        self.processor_records.append({
            'processor': processor_name,
            'utilization': utilization
        })

    def create_gantt_chart(self):
        if not self.records_jobs:
            print("No job records to display for Gantt chart.")
            return None

        df = pd.DataFrame(self.records_jobs)
        df['start'] = df['t_processing_start']
        df['finish'] = df['t_processing_end']
        df['Task'] = df['process'] + "_" + df['machine'].astype(str)

        fig = px.timeline(
            df,
            x_start="start",
            x_end="finish",
            y="Task",
            color="process",
            hover_data=["job_id"]
        )
        fig.update_yaxes(autorange="reversed")

        # x축을 linear 스케일로 강제
        fig.update_layout(xaxis_type='linear')

        return fig

    def summarize_results(self):
        df_jobs = pd.DataFrame(self.records_jobs)
        if df_jobs.empty:
            print("No job data available for summary.")
            return

        df_jobs['waiting_time'] = df_jobs['t_processing_start'] - \
            df_jobs['t_queue_in']
        df_jobs['processing_time'] = df_jobs['t_processing_end'] - \
            df_jobs['t_processing_start']
        df_jobs['flow_time'] = df_jobs['t_processing_end'] - \
            df_jobs['t_queue_in']

        group_proc = df_jobs.groupby('process')
        waiting_mean = group_proc['waiting_time'].mean()
        waiting_std = group_proc['waiting_time'].std()
        processing_mean = group_proc['processing_time'].mean()
        processing_std = group_proc['processing_time'].std()
        flow_time_mean = group_proc['flow_time'].mean()
        flow_time_std = group_proc['flow_time'].std()

        print("\n=== Process별 통계 ===")
        for proc in group_proc.groups.keys():
            print(f"[{proc}]")
            print(
                f" - 평균 대기시간: {waiting_mean[proc]:.2f} hrs, 표준편차: {waiting_std[proc]:.2f}")
            print(
                f" - 평균 처리시간: {processing_mean[proc]:.2f} hrs, 표준편차: {processing_std[proc]:.2f}")
            print(
                f" - 평균 체류시간: {flow_time_mean[proc]:.2f} hrs, 표준편차: {flow_time_std[proc]:.2f}")


sim_logger = SimulationLogger()
