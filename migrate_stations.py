"""
Migration: introduce stations table.
stations sit between locations and instruments.
instruments.location_id  →  instruments.station_id
"""
import sqlite3

conn = sqlite3.connect("env_instruments.db")
conn.execute("PRAGMA foreign_keys = OFF")

cur = conn.cursor()

# 1. create stations table
cur.execute("""
    CREATE TABLE IF NOT EXISTS stations (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL UNIQUE,
        location_id INTEGER REFERENCES locations(id),
        notes       TEXT
    )
""")

# 2. for every location that already has instruments, create a default station
cur.execute("""
    INSERT OR IGNORE INTO stations (name, location_id)
    SELECT l.name, l.id
    FROM locations l
    WHERE l.id IN (SELECT DISTINCT location_id FROM instruments WHERE location_id IS NOT NULL)
""")

# 3. rebuild instruments without location_id, adding station_id
cur.execute("""
    CREATE TABLE instruments_new (
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
    )
""")

cur.execute("""
    INSERT INTO instruments_new
        (id, serial_number, instrument_type_id, station_id,
         installed_date, cal_high_date, cal_low_date,
         part1, part2, part3, part4, notes)
    SELECT
        i.id, i.serial_number, i.instrument_type_id,
        s.id,
        i.installed_date, i.cal_high_date, i.cal_low_date,
        i.part1, i.part2, i.part3, i.part4, i.notes
    FROM instruments i
    LEFT JOIN stations s ON s.location_id = i.location_id
""")

cur.execute("DROP TABLE instruments")
cur.execute("ALTER TABLE instruments_new RENAME TO instruments")

conn.execute("PRAGMA foreign_keys = ON")
conn.commit()
conn.close()
print("Migration complete.")
