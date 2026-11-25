import json
from contextlib import contextmanager

import pytest

from utils import db


class FakeCursor:
    def __init__(self, rows, log):
        self.rows, self.log = rows, log

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, q):
        self.log.append(q)

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows):
        self.rows, self.queries, self.closed = rows, [], False

    def cursor(self):
        return FakeCursor(self.rows, self.queries)

    def close(self):
        self.closed = True


def row(course="CN", mega="Alpha", pod="Blue Rays", slot="4",
        lead=("Lee", "Lead", "LEAD@x.org"), ta=("Tia", "Ta", "Ta@x.org"),
        pta=("Pat", "Proj", "pta@x.org"), student=("Sam", "Student", "Sam@X.org")):
    return (course, mega, pod, slot, *lead, *ta, *pta, *student)


@contextmanager
def _conn_ctx(conn):
    yield conn


def patch_connect(monkeypatch, rows):
    conn = FakeConnection(rows)
    monkeypatch.setattr(db, "connect_to_db", lambda: _conn_ctx(conn))
    return conn


def test_rows_to_pod_data(snapshot):
    rows = [
        row(),
        row(student=("Zed", "Two", "zed@x.org")),                      # same pod, second student
        row(pod="Green Owls", slot="3", student=("Amy", "Three", "amy@x.org")),  # 2nd pod, same megapod
        row(mega="Beta", pod="Red Fox", student=("Bo", "Four", "bo@x.org"),
            ta=("Tom", "Other", "tom@x.org")),                            # 2nd megapod, other TA
        row(course="DL", mega="Gamma", pod="Pod9", student=("Cy", "Five", "cy@x.org")),  # 2nd course
    ]
    out = db.get_pod_data_from_db(FakeConnection(rows))
    snapshot("pod_data_basic", out)
    assert "sam@x.org" in out["CN"]["users"]  # emails lowercased
    assert out["CN"]["users"]["lead@x.org"]["megapods"] == ["Alpha", "Beta"]


def test_first_seen_role_wins():
    # TA address appears first as a student, later as the TA: role stays "student"
    rows = [row(student=("Tia", "Ta", "ta@x.org"), ta=("T", "T", "other@x.org")),
            row(pod="P2")]
    out = db.get_pod_data_from_db(FakeConnection(rows))
    assert out["CN"]["users"]["ta@x.org"]["role"] == "student"


def test_sql_query_snapshot(snapshot):
    conn = FakeConnection([])
    db.get_pod_data_from_db(conn)
    snapshot("pod_query", conn.queries)


def test_empty_result():
    assert db.get_pod_data_from_db(FakeConnection([])) == {}


@pytest.mark.known_bug("NULL TA email crashes with AttributeError (.lower() on None)")
def test_null_ta_email_raises():
    with pytest.raises(AttributeError):
        db.get_pod_data_from_db(FakeConnection([row(ta=(None, None, None))]))


def test_missing_name_prints_but_still_builds(capsys):
    # student without email+name: assertion trips, pod reported, but nothing is actually skipped
    out = db.get_pod_data_from_db(FakeConnection([row(student=(None, None, ""))]))
    assert "missing information for pod Blue Rays, skipping db entries" in capsys.readouterr().out
    assert "Blue Rays" in out["CN"]["structure"]["Alpha"]


@pytest.mark.known_bug("student with email but no first name -> TypeError")
def test_student_without_first_name_raises():
    with pytest.raises(TypeError):
        db.get_pod_data_from_db(FakeConnection([row(student=(None, "X", "x@x.org"))]))


async def test_poll_db_writes_when_changed(data_dir, monkeypatch, capsys):
    patch_connect(monkeypatch, [row()])
    (data_dir / "pods.json").write_text("{}")
    await db.poll_db.coro()
    written = json.loads((data_dir / "pods.json").read_text())
    assert "CN" in written
    out = capsys.readouterr().out
    assert "Polled db" in out and "Pod data has been changed" in out


async def test_poll_db_no_write_when_unchanged(data_dir, monkeypatch, capsys):
    rows = [row()]
    (data_dir / "pods.json").write_text(json.dumps(db.get_pod_data_from_db(FakeConnection(rows))))
    before = (data_dir / "pods.json").stat().st_mtime_ns
    patch_connect(monkeypatch, rows)
    await db.poll_db.coro()
    assert (data_dir / "pods.json").stat().st_mtime_ns == before
    assert "Pod data has been changed" not in capsys.readouterr().out


async def test_poll_db_first_run_never_creates_file(data_dir, monkeypatch, capsys):
    patch_connect(monkeypatch, [row()])
    await db.poll_db.coro()
    assert not (data_dir / "pods.json").exists()
    assert "Error occurred while getting data" in capsys.readouterr().out


async def test_poll_db_swallows_query_errors(data_dir, monkeypatch, capsys):
    patch_connect(monkeypatch, [row(ta=(None, None, None))])
    await db.poll_db.coro()
    assert "Error occurred while getting data" in capsys.readouterr().out


def test_save_data_to_json(data_dir):
    db.save_data_to_json({"a": 1}, "pods.json")
    assert json.loads((data_dir / "pods.json").read_text()) == {"a": 1}


def test_connect_to_db_uses_env_and_closes(monkeypatch):
    for k, v in dict(PG_HOST="h", PG_PORT="5432", PG_DATABASE="d", PG_USER="u", PG_PASSWORD="p").items():
        monkeypatch.setenv(k, v)
    seen = {}
    conn = FakeConnection([])

    def fake_connect(**kw):
        seen.update(kw)
        return conn

    monkeypatch.setattr(db.psycopg2, "connect", fake_connect)
    with db.connect_to_db() as c:
        assert c is conn and not conn.closed
    assert conn.closed
    assert seen == dict(host="h", port="5432", dbname="d", user="u", password="p")
