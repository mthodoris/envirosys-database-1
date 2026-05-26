"""
Export env_instruments.db → docs/data.json
Run this whenever you update the database, then push to GitHub.
"""
import sqlite3, json, os

DB_PATH  = "env_instruments.db"
OUT_DIR  = "docs"
OUT_FILE = os.path.join(OUT_DIR, "data.json")

os.makedirs(OUT_DIR, exist_ok=True)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

stations = conn.execute("""
    SELECT s.id, s.name, l.name AS location, s.notes
    FROM stations s
    LEFT JOIN locations l ON l.id = s.location_id
    ORDER BY s.name
""").fetchall()

output = []
for s in stations:
    instruments = conn.execute("""
        SELECT t.model, t.pollutant, i.serial_number,
               i.installed_date, i.cal_high_date, i.cal_low_date,
               i.part1, i.part2, i.part3, i.part4, i.notes
        FROM instruments i
        JOIN instrument_types t ON t.id = i.instrument_type_id
        WHERE i.station_id = ?
        ORDER BY t.model
    """, (s["id"],)).fetchall()

    output.append({
        "station":  s["name"],
        "location": s["location"] or "",
        "notes":    s["notes"] or "",
        "instruments": [dict(r) for r in instruments],
    })

conn.close()

with open(OUT_FILE, "w") as f:
    json.dump(output, f, indent=2)

print(f"Exported {len(output)} stations → {OUT_FILE}")
