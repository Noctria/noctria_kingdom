from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

PATHS = {
    "airflow_docker": BASE_DIR / "airflow_docker",
    "execution": BASE_DIR / "execution",
    "experts": BASE_DIR / "experts",
    "llm_server": BASE_DIR / "llm_server",
    "logs": BASE_DIR / "logs",
    "noctria_gui": BASE_DIR / "noctria_gui",
    "tests": BASE_DIR / "tests",
    "tools": BASE_DIR / "tools",
    "veritas": BASE_DIR / "veritas",
    "system_start": BASE_DIR / "system_start",
}
