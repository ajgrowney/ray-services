from datetime import timedelta
import pendulum
import requests
from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator

def call_good_morning():
    res = requests.post("http://localhost:5001/controller/microphone/input",json={"event": "input/message", "text": "good morning"})
    return res.json()

default_args = {
    'owner': 'ajgrowney',
    'depends_on_past': False,
    'email': ['ajgrowney@gmail.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0
}

with DAG( 'good_morning', description='Trigger Morning Routine',
    default_args=default_args,
    schedule_interval="0 6 * * 1-5",
    start_date=pendulum.create(2020,11,17,tz="US/Mountain"),
    tags=['todo'],
) as good_morning_dag:
    t1 = PythonOperator(task_id="nlu_request",python_callable=call_good_morning)
    t2 = BashOperator(task_id="bash_task",bash_command="echo 'Success'")
    t1.set_downstream(t2)
