from packages.db.store import Store


def test_repeatable_migrations_preserve_records(tmp_path, monkeypatch):
    monkeypatch.setenv("SHADOWLAB_DATA_DIR", str(tmp_path))
    db = Store(f"sqlite:///{tmp_path / 'migration.db'}")
    db.initialize()
    record = db.put("finding", {"state": "CONFIRMED", "evidence": [{"status": 200}]})
    db.initialize()
    assert db.get("finding", record["id"])["evidence"][0]["status"] == 200
    with db.engine.connect() as connection:
        assert connection.exec_driver_sql("select version_num from alembic_version").scalar_one() == "001"
