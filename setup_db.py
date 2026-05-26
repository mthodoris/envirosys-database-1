import sqlite3

DB_PATH = "env_instruments.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.executescript("""
    CREATE TABLE IF NOT EXISTS instrument_types (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        model   TEXT NOT NULL UNIQUE,   -- e.g. APNA, APMA, APSA
        pollutant TEXT NOT NULL         -- e.g. NOx, CO, SO2
    );

    CREATE TABLE IF NOT EXISTS locations (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        name    TEXT NOT NULL UNIQUE,
        notes   TEXT
    );

    CREATE TABLE IF NOT EXISTS stations (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL UNIQUE,
        location_id INTEGER REFERENCES locations(id),
        notes       TEXT
    );

    CREATE TABLE IF NOT EXISTS instruments (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        serial_number       TEXT NOT NULL UNIQUE,
        instrument_type_id  INTEGER NOT NULL REFERENCES instrument_types(id),
        station_id          INTEGER REFERENCES stations(id),
        installed_date      TEXT,
        cal_high_date       TEXT,
        cal_low_date        TEXT,
        part1               TEXT,
        part2               TEXT,
        part3               TEXT,
        part4               TEXT,
        notes               TEXT
    );
""")

# Seed the three instrument types
cur.executemany(
    "INSERT OR IGNORE INTO instrument_types (model, pollutant) VALUES (?, ?)",
    [
        ("APNA", "NOx"),
        ("APMA", "CO"),
        ("APSA", "SO2"),
    ],
)

conn.commit()
conn.close()
print(f"Database created at {DB_PATH}")
print("Tables: instrument_types, locations, instruments")
