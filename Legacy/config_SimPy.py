import random


# 시뮬레이션 총 시간(일 단위)
SIM_TIME = 14  # 14 days

# Build 공정에서 불량품이 발생하는 확률
DEFECT_RATE_PROC_BUILD = 0.01

# -------------------------------
# 머신/워커 수를 여기서 설정
# -------------------------------
NUM_MACHINES_BUILD = 2   # Build 공정의 3D프린터 수
NUM_MACHINES_WASH = 1    # Wash 공정의 세척기 수
NUM_MACHINES_DRY = 1     # Dry 공정의 건조기 수
NUM_WORKERS_IN_INSPECT = 3  # Inspect 공정의 워커(검수자) 수

# -------------------------------
# 랜덤값 설정 (lambda 사용)
# -------------------------------


# def NUM_PATIENTS_PER_ORDER(): return random.randint(10, 15)
# def NUM_ITEMS_PER_PATIENT(): return random.randint(50, 100)
def NUM_PATIENTS_PER_ORDER(): return random.randint(3, 5)
def NUM_ITEMS_PER_PATIENT(): return random.randint(5, 10)


# Pallet(또는 Job)당 아이템 최대 개수
PALLET_SIZE_LIMIT = 50

# 불량 아이템을 모아 재작업 Job으로 만들 때, 몇 개까지 모을지
POLICY_NUM_DEFECT_PER_JOB = 20

# 재작업 Job을 Proc_Build 큐에 넣을 때 어느 위치에 넣을지
POLICY_REPROC_SEQ_IN_QUEUE = "QUEUE_LAST"

# 큐에서 Job을 할당할 때의 디스패치 정책
POLICY_DISPATCH_FROM_QUEUE = "FIFO"

# Order 내부의 각 Patient 아이템을 여러 Job으로 분할하는 정책
# "EQUAL_SPLIT" or "MAX_PACK"
POLICY_ORDER_TO_JOB = "EQUAL_SPLIT"

# Customer가 Order를 생성하는 주기(일 단위)
CUST_ORDER_CYCLE = 7
# Order를 납품하기까지 주어진 일 수(일 단위)
CUST_ORDER_DUE = 7

BUILD_MACHINE_TIME_HOURS = 1
WASH_MACHINE_TIME_HOURS = 1
DRY_MACHINE_TIME_HOURS = 1
INSPECT_WORKER_TIME_HOURS = 0.1

# -------------------------------
# 로그/시각화 제어 플래그
# -------------------------------
FLAG_PRINT_EVENT_LOG = True   # True면 이벤트 로그를 기록/출력
FLAG_SHOW_PLOTLY = True       # True면 시뮬레이션 종료 후 Plotly 차트 표시
