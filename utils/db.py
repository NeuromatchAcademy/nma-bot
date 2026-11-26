import asyncio
import json
import logging
import os
from contextlib import contextmanager
from pathlib import Path

import psycopg2
from discord.ext import tasks
from dotenv import load_dotenv

from .paths import data_path

log = logging.getLogger(__name__)


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


def _person(cols):
    """(full name, lowercased email) from (first, last, email) columns, or None if unusable."""
    first, last, email = cols
    if not first or not email:
        return None
    return f"{first} {last or ''}".strip(), email.strip().lower()


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
        # column_names = [desc[0] for desc in cursor.description[13:]]

        pod_data = {}
        pods_missing_data = []
        for row in results:
            course_key, megapod_key, pod_key, pod_time_slot = row[0], row[1], row[2], row[3]
            # LEFT JOINs: any of these people may be absent (NULL columns).
            people = [
                ("student", _person(row[13:16])),
                ("lead_ta", _person(row[4:7])),
                ("ta", _person(row[7:10])),
                ("project_ta", _person(row[10:13])),
            ]
            if any(person is None for _, person in people) and pod_key not in pods_missing_data:
                pods_missing_data.append(pod_key)

            course = pod_data.setdefault(course_key, {"structure": {}, "users": {}})
            pods = course["structure"].setdefault(megapod_key, [])
            if pod_key not in pods:
                pods.append(pod_key)

            # a person appearing in several roles keeps the first role seen
            for role, person in people:
                if person is None:
                    continue
                name, email = person
                entry = course["users"].setdefault(email, {
                    "name": name,
                    "role": role,
                    "timeslot": pod_time_slot,
                    "megapods": [],
                    "pods": [],
                })
                if megapod_key not in entry["megapods"]:
                    entry["megapods"].append(megapod_key)
                if pod_key not in entry["pods"]:
                    entry["pods"].append(pod_key)

        for pod in pods_missing_data:
            log.warning("incomplete information for pod %s; missing people were left out", pod)

    return pod_data


def save_data_to_json(data, filename):
    """Write atomically so a crash mid-write cannot leave a corrupt file behind."""
    file_path = data_path(filename)
    tmp_path = file_path.with_name(file_path.name + ".tmp")
    with open(tmp_path, 'w') as f:
        json.dump(data, f)
    os.replace(tmp_path, file_path)


def load_pods(path):
    """Return the stored pod data, or {} if the file is missing or unreadable."""
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _fetch_pod_data():
    with connect_to_db() as connection:
        return get_pod_data_from_db(connection)


@tasks.loop(seconds=60)
async def poll_db():
    try:
        # psycopg2 and file I/O block, so keep them off the event loop
        new_data = await asyncio.to_thread(_fetch_pod_data)
        log.debug("Polled db")
        old_data = await asyncio.to_thread(load_pods, data_path('pods.json'))
        if old_data != new_data:
            log.info("Pod data has been changed")
            await asyncio.to_thread(save_data_to_json, new_data, 'pods.json')
    except Exception:
        log.exception("Error occurred while getting data")


async def main():
    await poll_db()


if __name__ == "__main__":
    asyncio.run(main())
