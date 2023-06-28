import os
import json
import asyncio
import psycopg2
from pathlib import Path
from dotenv import load_dotenv
from contextlib import contextmanager


@contextmanager
def connect_to_db():
    current_dir = Path(__file__).resolve().parent
    parent_dir = current_dir.parent
    env_file_path = parent_dir / ".dbenv"
    load_dotenv(dotenv_path=env_file_path)

    postgres_host = os.getenv("PG_HOST")
    postgres_port = os.getenv("PG_PORT")
    postgres_database = os.getenv("PG_DATABASE")
    postgres_user = os.getenv("PG_USER")
    postgres_password = os.getenv("PG_PASSWORD")

    connection = psycopg2.connect(
        host=postgres_host,
        port=postgres_port,
        dbname=postgres_database,
        user=postgres_user,
        password=postgres_password
    )
    try:
        yield connection
    finally:
        connection.close()


def get_pod_data_from_db(connection):
    with connection.cursor() as cursor:
        query = "SELECT c.name, mp.name, cp.name, cp.time_slot, \
            ulta.first_name, ulta.last_name, ulta.email, \
            uta.first_name, uta.last_name, uta.email, \
            upta.first_name, upta.last_name, upta.email, \
            u.first_name, u.last_name, u.email FROM \
            course_coursepod cp LEFT JOIN course_coursemegapod \
            mp ON cp.mega_pod_id=mp.id LEFT JOIN course_podstudent \
            ps ON cp.id=ps.pod_id LEFT JOIN course_coursetaapplication \
            ta ON ta.id=mp.lead_ta_id LEFT JOIN course_coursetaapplication \
            ta2 ON ta2.id=cp.ta_id LEFT JOIN course_coursetaapplication \
            ta3 ON ta3.id=cp.project_ta_id LEFT JOIN course_coursestudentapplication \
            sa ON ps.student_id=sa.id LEFT JOIN course_course \
            c ON c.id=sa.course_id LEFT JOIN users_user \
            u ON u.id=sa.user_id LEFT JOIN users_user \
            ulta ON ulta.id=ta.user_id LEFT JOIN users_user \
            uta ON uta.id=ta2.user_id LEFT JOIN users_user \
            upta ON upta.id=ta3.user_id WHERE c.is_active IS true;"
        cursor.execute(query)
        results = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description[13:]]

        pod_data = {}
        for row in results:
            course_key = row[0]
            megapod_key = row[1]
            pod_key = row[2]
            pod_time_slot = row[3]
            lead_ta_fn = row[4]
            lead_ta_ln = row[5]
            lead_ta_email = row[6]
            ta_fn = row[7]
            ta_ln = row[8]
            ta_email = row[9]
            project_ta_fn = row[10]
            project_ta_ln = row[11]
            project_ta_email = row[12]
            item = {column_names[i]: value for i, value in enumerate(row[13:])}
            if course_key not in pod_data:
                pod_data[course_key] = {}
            if megapod_key not in pod_data[course_key]:
                pod_data[course_key][megapod_key] = {}
                pod_data[course_key][megapod_key]['lead_ta'] = {
                    'first_name': lead_ta_fn,
                    'last_name': lead_ta_ln,
                    'email': lead_ta_email
                }
                pod_data[course_key][megapod_key]['pods'] = {}
            if pod_key not in pod_data[course_key][megapod_key]['pods']:
                pod_data[course_key][megapod_key]['pods'][pod_key] = {}
                pod_data[course_key][megapod_key]['pods'][pod_key][
                    'time_slot'
                ] = pod_time_slot
                pod_data[course_key][megapod_key]['pods'][pod_key]['ta'] = {
                    'first_name': ta_fn,
                    'last_name': ta_ln,
                    'email': ta_email
                }
                pod_data[course_key][megapod_key]['pods'][pod_key][
                    'project_ta'
                ] = {
                    'first_name': project_ta_fn,
                    'last_name': project_ta_ln,
                    'email': project_ta_email
                }
                pod_data[course_key][megapod_key]['pods'][pod_key][
                    'students'
                ] = []
            pod_data[course_key][megapod_key]['pods'][pod_key][
                'students'
            ].append(item)
    return pod_data


def save_data_to_json(data, filename):
    current_dir = Path(__file__).resolve().parent
    parent_dir = current_dir.parent
    file_path = parent_dir / filename
    with open(file_path, 'w') as f:
        json.dump(data, f)


async def poll_db():
    with connect_to_db() as connection:
        data = get_pod_data_from_db(connection)
        save_data_to_json(data, 'pods.json')
        while True:
            await asyncio.sleep(60)
            try:
                new_data = get_pod_data_from_db(connection)
            except Exception as e:
                print(f"Error occurred while getting data: {e}")

            if data != new_data:
                print("Data has been changed")
                save_data_to_json(new_data, 'pods.json')
            data = new_data


async def main():
    await poll_db()


if __name__ == "__main__":
    asyncio.run(main())
