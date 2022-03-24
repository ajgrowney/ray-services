import os
import subprocess
from airflow import DAG
from airflow.operators.http_operator import SimpleHttpOperator

def call_good_morning():
    res = requests.post("http://localhost:5001/controller/microphone/input",json={"event": "input/message", "text": "good morning"})
    return res.json()

class Scheduler:
    def __init__(self):
        self.airflow_pid = None
        self.entry = ["airflow", "scheduler"]
        self.dags = [ ]
        self.default_args = {
            'owner': 'ajgrowney',
            'depends_on_past': False,
            'email': ['ajgrowney@gmail.com'],
            'email_on_failure': False,
            'email_on_retry': False,
            'retries': 0,
        }
        


    def start(self):
        self.airflow_pid = subprocess.Popen(self.entry, stdout=subprocess.PIPE)
        
    def run_good_morning(self):
        with DAG(
            'good_morning',
            default_args=self.default_args,
            description='A simple DAG to say hello',
            schedule_interval=timedelta(minutes=1),
            start_date=days_ago(0),
            tags=['intro'],
            max_active_runs=1
        ) as good_morning_dag:
            t1 = PythonOperator(task_id="nlu_request",python_callable=call_good_morning)
            t2 = BashOperator(task_id="bash_task",bash_command="echo 'Success'")
            t1.set_downstream(t2)


    def shutdown(self):
        if self.airflow_pid:
            os.kill(self.airflow_pid.pid,9)
        return { "status": 202 }