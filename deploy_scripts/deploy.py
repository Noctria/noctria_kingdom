import subprocess
import os
import datetime
import shutil

# AirflowのDAG配置ディレクトリ（環境に合わせて変更してください）
AIRFLOW_DAGS_DIR = "/opt/airflow/dags/generated"
GENERATED_CODE_DIR = "./generated_code"

def copy_generated_code():
    os.makedirs(AIRFLOW_DAGS_DIR, exist_ok=True)
    for filename in os.listdir(GENERATED_CODE_DIR):
        if filename.endswith(".py"):
            src = os.path.join(GENERATED_CODE_DIR, filename)
            dst = os.path.join(AIRFLOW_DAGS_DIR, filename)
            shutil.copy2(src, dst)
            print(f"Copied {filename} to Airflow DAGs folder.")

def docker_build_and_push(tag):
    try:
        subprocess.run(["docker", "build", "-t", tag, "."], check=True)
        subprocess.run(["docker", "push", tag], check=True)
        print(f"Docker image {tag} built and pushed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error during Docker build/push: {e}")

def main():
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    tag = f"yourdockerhubusername/noctria_trade_ai:{timestamp}"

    print("Copying generated code to Airflow DAG folder...")
    copy_generated_code()

    print("Building and pushing Docker image...")
    docker_build_and_push(tag)

    print("Deployment completed.")

if __name__ == "__main__":
    main()
