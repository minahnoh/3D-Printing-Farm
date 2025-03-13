# config_SimPy.py
import random

# Simulation time settings
SIM_TIME = 14 * 24 * 60  # (unit: minutes)

# Process settings
DEFECT_RATE_PROC_BUILD = 0.00  # 5% defect rate in build process
NUM_WORKERS_IN_INSPECT = 5  # Number of workers in inspection process

# Logging and visualization settings
EVENT_LOGGING = False  # Event logging enable/disable flag
DETAILED_STATS_ENABLED = False  # Detailed statistics display flag
# SHOW_JOB_HIST = True  # 기본값은 False로 설정

# Visualization flags
GANTT_CHART_ENABLED = False  # Gantt chart visualization enable/disable flag
VIS_STAT_ENABLED = False  # Statistical graphs visualization enable/disable flag
SHOW_GANTT_DEBUG = False  # 기본값은 False로 설정

# Order and item settings


def NUM_PATIENTS_PER_ORDER(): return random.randint(
    5, 5)  # Number of patients per order


def NUM_ITEMS_PER_PATIENT(): return random.randint(
    5, 10)  # Number of items per patient


PALLET_SIZE_LIMIT = 50  # Maximum items in one pallet

# Customer settings
CUST_ORDER_CYCLE = 7 * 24 * 60  # Customer order cycle (1 week in minutes)

# Policy settings
POLICY_NUM_DEFECT_PER_JOB = 20  # Number of defective items to collect for rework
# Policy for placing rework jobs in queue
POLICY_REPROC_SEQ_IN_QUEUE = "QUEUE_LAST"
POLICY_DISPATCH_FROM_QUEUE = "FIFO"  # Policy for extracting jobs from queue
POLICY_ORDER_TO_JOB = "EQUAL_SPLIT"  # Policy for dividing orders into jobs

# Process time settings (in minutes)
PROC_TIME_BUILD = 120  # Process time for build (unit: minutes)
PROC_TIME_WASH = 60  # Process time for wash (unit: minutes)
PROC_TIME_DRY = 60  # Process time for dry (unit: minutes)
PROC_TIME_INSPECT = 10  # Process time for inspect per item (unit: minutes)

# Machine settings
NUM_MACHINES_BUILD = 3  # Number of 3D print machines
NUM_MACHINES_WASH = 1  # Number of wash machines
NUM_MACHINES_DRY = 1  # Number of dry machines
CAPACITY_MACHINE_BUILD = 2  # Job capacity for build machines
CAPACITY_MACHINE_WASH = 2  # Job capacity for wash machines
CAPACITY_MACHINE_DRY = 2  # Job capacity for dry machines

# Order settings
ORDER_DUE_DATE = 7 * 24 * 60  # Order due date (1 week in minutes)
