from pathlib import Path

ROOT_PATH = Path(__file__).parent.parent.parent

# Data files
# ----------------------------------------------------------------------------------------------------------------------

DATA_PATH = ROOT_PATH / "data"
HOST_SPECS_PATH = DATA_PATH / "host_specs.json"
WORKFLOW_FILES = [
    DATA_PATH / "pegasus_workflows" / "sipht.dag",
]


# Model related
# ----------------------------------------------------------------------------------------------------------------------

MAX_OBS_SIZE = 100_000
MAX_TRAINING_DS_SEED = 1_000_000_000
MIN_TESTING_DS_SEED = MAX_TRAINING_DS_SEED + 1

# Evaluation related
# ----------------------------------------------------------------------------------------------------------------------

DEFAULT_MODEL_DIR = ROOT_PATH / "logs"
ALGORITHMS = [
    ("CP-SAT", "cp_sat"),
    ("Round Robin", "round_robin"),
    ("Min-Min", "min_min"),
    ("Best Fit", "best_fit"),
    ("Max-Min", "max_min"),
    ("HEFT", "heft"),
]
