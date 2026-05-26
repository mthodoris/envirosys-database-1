import sqlite3
import sys
from datetime import date

DB_PATH = "env_instruments.db"


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ── helpers ────────────────────────────────────────────────────────────────────

def prompt(label, required=True):
    while True:
        val = input(f"  {label}: ").strip()
        if val:
            return val
        if not required:
            return None
        print("  (required — please enter a value)")


def pick(label, rows, key):
    if not rows:
        print(f"  No {label} found. Add one first.")
        return None
    print(f"\n  {label}:")
    for i, row in enumerate(rows, 1):
        print(f"    {i}. {row[key]}")
    while True:
        raw = input(f"  Choose 1–{len(rows)}: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(rows):
            return rows[int(raw) - 1]["id"]
        print("  Invalid choice.")


def date_input(label):
    val = input(f"  {label} (YYYY-MM-DD, or blank): ").strip()
    return val if val else None


def hr():
    print("\n" + "─" * 50)


# ── locations ──────────────────────────────────────────────────────────────────

def add_location(conn):
    hr()
    print("ADD LOCATION")
    name  = prompt("Location name")
    notes = prompt("Notes (optional)", required=False)
    try:
        conn.execute("INSERT INTO locations (name, notes) VALUES (?, ?)", (name, notes))
        conn.commit()
        print(f"  ✓ Location '{name}' added.")
    except sqlite3.IntegrityError:
        print(f"  Location '{name}' already exists.")


def list_locations(conn):
    hr()
    print("LOCATIONS")
    rows = conn.execute("SELECT * FROM locations ORDER BY name").fetchall()
    if not rows:
        print("  No locations yet.")
        return
    for r in rows:
        note = f"  — {r['notes']}" if r["notes"] else ""
        print(f"\n  [{r['id']}] {r['name']}{note}")
        stations = conn.execute(
            "SELECT * FROM stations WHERE location_id = ? ORDER BY name", (r["id"],)
        ).fetchall()
        if not stations:
            print("    (no stations)")
        for s in stations:
            instruments = conn.execute("""
                SELECT t.model, t.pollutant, i.serial_number
                FROM instruments i
                JOIN instrument_types t ON t.id = i.instrument_type_id
                WHERE i.station_id = ?
                ORDER BY t.model
            """, (s["id"],)).fetchall()
            print(f"    · Station: {s['name']}")
            if instruments:
                for inst in instruments:
                    print(f"        {inst['model']} ({inst['pollutant']})  SN: {inst['serial_number']}")
            else:
                print("        (no instruments)")
    print()


def edit_location(conn):
    hr()
    print("EDIT LOCATION")
    rows = conn.execute("SELECT * FROM locations ORDER BY name").fetchall()
    if not rows:
        print("  No locations yet.")
        return
    for i, r in enumerate(rows, 1):
        print(f"    {i}. {r['name']}")
    while True:
        raw = input(f"  Choose 1–{len(rows)}: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(rows):
            loc = rows[int(raw) - 1]
            break
        print("  Invalid choice.")

    print("  (Press Enter to keep current value)\n")
    new_name = input(f"  Name [{loc['name']}]: ").strip() or loc["name"]
    new_notes = input(f"  Notes [{loc['notes'] or ''}]: ").strip()
    new_notes = new_notes if new_notes else loc["notes"]

    try:
        conn.execute(
            "UPDATE locations SET name = ?, notes = ? WHERE id = ?",
            (new_name, new_notes, loc["id"]),
        )
        conn.commit()
        print(f"  ✓ Location updated to '{new_name}'.")
    except sqlite3.IntegrityError:
        print(f"  A location named '{new_name}' already exists.")


def remove_location(conn):
    hr()
    print("REMOVE LOCATION")
    rows = conn.execute("SELECT * FROM locations ORDER BY name").fetchall()
    if not rows:
        print("  No locations yet.")
        return
    for i, r in enumerate(rows, 1):
        print(f"    {i}. {r['name']}")
    while True:
        raw = input(f"  Choose 1–{len(rows)}: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(rows):
            loc = rows[int(raw) - 1]
            break
        print("  Invalid choice.")

    confirm = input(f"  Delete '{loc['name']}'? Stations using it will lose their location. [y/N]: ").strip().lower()
    if confirm != "y":
        print("  Cancelled.")
        return

    conn.execute("DELETE FROM locations WHERE id = ?", (loc["id"],))
    conn.commit()
    print(f"  ✓ Location '{loc['name']}' removed.")


# ── stations ───────────────────────────────────────────────────────────────────

def add_station(conn):
    hr()
    print("ADD STATION")
    name = prompt("Station name (e.g. MAM11)")

    locs = conn.execute("SELECT * FROM locations ORDER BY name").fetchall()
    if not locs:
        print("  No locations yet — add a location first.")
        return
    loc_id = pick("Location", locs, "name")
    if loc_id is None:
        return

    notes = prompt("Notes (optional)", required=False)
    try:
        conn.execute(
            "INSERT INTO stations (name, location_id, notes) VALUES (?, ?, ?)",
            (name, loc_id, notes),
        )
        conn.commit()
        print(f"  ✓ Station '{name}' added.")
    except sqlite3.IntegrityError:
        print(f"  Station '{name}' already exists.")


def list_stations(conn):
    hr()
    print("STATIONS")
    rows = conn.execute("""
        SELECT s.id, s.name, l.name AS location, s.notes
        FROM stations s
        LEFT JOIN locations l ON l.id = s.location_id
        ORDER BY s.name
    """).fetchall()
    if not rows:
        print("  No stations yet.")
        return

    for s in rows:
        instruments = conn.execute("""
            SELECT t.model, t.pollutant, i.serial_number
            FROM instruments i
            JOIN instrument_types t ON t.id = i.instrument_type_id
            WHERE i.station_id = ?
            ORDER BY t.model
        """, (s["id"],)).fetchall()

        loc = s["location"] or "—"
        print(f"\n  {s['name']}  ({loc})")
        if instruments:
            for inst in instruments:
                print(f"    · {inst['model']} ({inst['pollutant']})  SN: {inst['serial_number']}")
        else:
            print("    (no instruments assigned)")
    print()


def edit_station(conn):
    hr()
    print("EDIT STATION")
    rows = conn.execute("""
        SELECT s.id, s.name, l.name AS location, s.notes
        FROM stations s
        LEFT JOIN locations l ON l.id = s.location_id
        ORDER BY s.name
    """).fetchall()
    if not rows:
        print("  No stations yet.")
        return
    for i, r in enumerate(rows, 1):
        print(f"    {i}. {r['name']}  ({r['location'] or '—'})")
    while True:
        raw = input(f"  Choose 1–{len(rows)}: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(rows):
            s = rows[int(raw) - 1]
            break
        print("  Invalid choice.")

    print("  (Press Enter to keep current value)\n")
    new_name  = input(f"  Name  [{s['name']}]: ").strip() or s["name"]
    new_notes = input(f"  Notes [{s['notes'] or ''}]: ").strip()
    new_notes = new_notes if new_notes else s["notes"]

    locs = conn.execute("SELECT * FROM locations ORDER BY name").fetchall()
    print(f"\n  Location (current: {s['location'] or '—'}) — press Enter to keep:")
    for i, l in enumerate(locs, 1):
        print(f"    {i}. {l['name']}")
    raw = input(f"  Choose 1–{len(locs)} or Enter to keep: ").strip()
    if raw.isdigit() and 1 <= int(raw) <= len(locs):
        new_loc_id = locs[int(raw) - 1]["id"]
    else:
        new_loc_id = conn.execute(
            "SELECT location_id FROM stations WHERE id = ?", (s["id"],)
        ).fetchone()[0]

    try:
        conn.execute(
            "UPDATE stations SET name = ?, notes = ?, location_id = ? WHERE id = ?",
            (new_name, new_notes, new_loc_id, s["id"]),
        )
        conn.commit()
        print(f"  ✓ Station updated to '{new_name}'.")
    except sqlite3.IntegrityError:
        print(f"  A station named '{new_name}' already exists.")


def remove_station(conn):
    hr()
    print("REMOVE STATION")
    rows = conn.execute("""
        SELECT s.id, s.name, l.name AS location
        FROM stations s
        LEFT JOIN locations l ON l.id = s.location_id
        ORDER BY s.name
    """).fetchall()
    if not rows:
        print("  No stations yet.")
        return
    for i, r in enumerate(rows, 1):
        print(f"    {i}. {r['name']}  ({r['location'] or '—'})")
    while True:
        raw = input(f"  Choose 1–{len(rows)}: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(rows):
            s = rows[int(raw) - 1]
            break
        print("  Invalid choice.")

    confirm = input(f"  Delete '{s['name']}'? Its instruments will be unassigned. [y/N]: ").strip().lower()
    if confirm != "y":
        print("  Cancelled.")
        return

    conn.execute("DELETE FROM stations WHERE id = ?", (s["id"],))
    conn.commit()
    print(f"  ✓ Station '{s['name']}' removed.")


# ── instruments ────────────────────────────────────────────────────────────────

def add_instrument(conn):
    hr()
    print("ADD INSTRUMENT")

    stations = conn.execute("""
        SELECT s.id, s.name, l.name AS location
        FROM stations s
        LEFT JOIN locations l ON l.id = s.location_id
        ORDER BY s.name
    """).fetchall()
    if not stations:
        print("  No stations yet — add a station first.")
        return

    print("\n  Station:")
    for i, s in enumerate(stations, 1):
        print(f"    {i}. {s['name']}  ({s['location'] or '—'})")
    while True:
        raw = input(f"  Choose 1–{len(stations)}: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(stations):
            station_id = stations[int(raw) - 1]["id"]
            break
        print("  Invalid choice.")

    types = conn.execute("SELECT * FROM instrument_types ORDER BY model").fetchall()
    type_id = pick("Instrument type", types, "model")
    if type_id is None:
        return

    serial = prompt("Serial number")

    today = date.today().isoformat()
    raw_date = input(f"  Installed date (YYYY-MM-DD) [{today}]: ").strip()
    installed = raw_date if raw_date else today

    cal_high = date_input("Cal. high concentration date")
    cal_low  = date_input("Cal. low  concentration date")

    print("  Inside parts (press Enter to skip):")
    part1 = input("    Part 1: ").strip() or None
    part2 = input("    Part 2: ").strip() or None
    part3 = input("    Part 3: ").strip() or None
    part4 = input("    Part 4: ").strip() or None

    notes = prompt("Notes (optional)", required=False)

    try:
        conn.execute(
            "INSERT INTO instruments "
            "(serial_number, instrument_type_id, station_id, installed_date, "
            " cal_high_date, cal_low_date, part1, part2, part3, part4, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (serial, type_id, station_id, installed,
             cal_high, cal_low, part1, part2, part3, part4, notes),
        )
        conn.commit()
        print(f"  ✓ Instrument {serial} added.")
    except sqlite3.IntegrityError:
        print(f"  Serial number '{serial}' already exists.")


def list_instruments(conn):
    hr()
    print("INSTRUMENTS")
    rows = conn.execute("""
        SELECT i.id, i.serial_number, t.model, t.pollutant,
               s.name AS station, l.name AS location,
               i.installed_date, i.cal_high_date, i.cal_low_date,
               i.part1, i.part2, i.part3, i.part4, i.notes
        FROM instruments i
        JOIN instrument_types t ON t.id = i.instrument_type_id
        LEFT JOIN stations    s ON s.id = i.station_id
        LEFT JOIN locations   l ON l.id = s.location_id
        ORDER BY s.name, t.model
    """).fetchall()
    if not rows:
        print("  No instruments yet.")
        return

    current_station = None
    for r in rows:
        if r["station"] != current_station:
            current_station = r["station"]
            loc = r["location"] or "—"
            print(f"\n  ── {current_station or '(no station)'}  [{loc}]")

        parts = [r[f"part{n}"] for n in range(1, 5) if r[f"part{n}"]]
        print(f"\n    {r['model']} ({r['pollutant']})  SN: {r['serial_number']}")
        print(f"    Installed:  {r['installed_date'] or '—'}")
        print(f"    Cal. high:  {r['cal_high_date']  or '—'}")
        print(f"    Cal. low:   {r['cal_low_date']   or '—'}")
        if parts:
            print(f"    Parts:      {', '.join(parts)}")
        if r["notes"]:
            print(f"    Notes:      {r['notes']}")
    print()


def edit_instrument(conn):
    hr()
    print("EDIT INSTRUMENT")
    rows = conn.execute("""
        SELECT i.id, i.serial_number, t.model, s.name AS station
        FROM instruments i
        JOIN instrument_types t ON t.id = i.instrument_type_id
        LEFT JOIN stations s ON s.id = i.station_id
        ORDER BY s.name, t.model
    """).fetchall()
    if not rows:
        print("  No instruments yet.")
        return

    print("\n  Instrument:")
    for i, r in enumerate(rows, 1):
        print(f"    {i}. {r['serial_number']}  {r['model']}  @ {r['station'] or '—'}")
    while True:
        raw = input(f"  Choose 1–{len(rows)}: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(rows):
            inst_id = rows[int(raw) - 1]["id"]
            break
        print("  Invalid choice.")

    r = conn.execute("SELECT * FROM instruments WHERE id = ?", (inst_id,)).fetchone()

    FIELDS = [
        ("installed_date", "Installed date"),
        ("cal_high_date",  "Cal. high concentration date"),
        ("cal_low_date",   "Cal. low  concentration date"),
        ("part1",          "Part 1"),
        ("part2",          "Part 2"),
        ("part3",          "Part 3"),
        ("part4",          "Part 4"),
        ("notes",          "Notes"),
    ]
    print("  (Press Enter to keep current value)\n")
    updates = {}
    for col, label in FIELDS:
        current = r[col] or ""
        val = input(f"  {label} [{current}]: ").strip()
        if val:
            updates[col] = val

    if updates:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(
            f"UPDATE instruments SET {set_clause} WHERE id = ?",
            list(updates.values()) + [inst_id],
        )
        conn.commit()
        print("  ✓ Instrument updated.")
    else:
        print("  No changes made.")


def move_instrument(conn):
    hr()
    print("MOVE INSTRUMENT TO ANOTHER STATION")
    rows = conn.execute("""
        SELECT i.id, i.serial_number, t.model, s.name AS station
        FROM instruments i
        JOIN instrument_types t ON t.id = i.instrument_type_id
        LEFT JOIN stations s ON s.id = i.station_id
        ORDER BY i.serial_number
    """).fetchall()
    inst_id = pick("Instrument (serial)", rows, "serial_number")
    if inst_id is None:
        return

    stations = conn.execute("""
        SELECT s.id, s.name, l.name AS location
        FROM stations s LEFT JOIN locations l ON l.id = s.location_id
        ORDER BY s.name
    """).fetchall()
    print("\n  New station:")
    for i, s in enumerate(stations, 1):
        print(f"    {i}. {s['name']}  ({s['location'] or '—'})")
    while True:
        raw = input(f"  Choose 1–{len(stations)}: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(stations):
            station_id = stations[int(raw) - 1]["id"]
            break
        print("  Invalid choice.")

    conn.execute("UPDATE instruments SET station_id = ? WHERE id = ?", (station_id, inst_id))
    conn.commit()
    print("  ✓ Station updated.")


# ── overview ───────────────────────────────────────────────────────────────────

def overview(conn):
    hr()
    print("FULL OVERVIEW  (Locations → Stations → Instruments)\n")
    locations = conn.execute("SELECT * FROM locations ORDER BY name").fetchall()
    if not locations:
        print("  No locations yet.")
        return
    for loc in locations:
        note = f"  — {loc['notes']}" if loc["notes"] else ""
        print(f"  LOCATION: {loc['name']}{note}")
        stations = conn.execute(
            "SELECT * FROM stations WHERE location_id = ? ORDER BY name", (loc["id"],)
        ).fetchall()
        if not stations:
            print("    (no stations)")
        for s in stations:
            snote = f"  — {s['notes']}" if s["notes"] else ""
            print(f"    STATION: {s['name']}{snote}")
            instruments = conn.execute("""
                SELECT t.model, t.pollutant, i.serial_number,
                       i.installed_date, i.cal_high_date, i.cal_low_date,
                       i.part1, i.part2, i.part3, i.part4, i.notes
                FROM instruments i
                JOIN instrument_types t ON t.id = i.instrument_type_id
                WHERE i.station_id = ?
                ORDER BY t.model
            """, (s["id"],)).fetchall()
            if not instruments:
                print("      (no instruments)")
            for inst in instruments:
                parts = [inst[f"part{n}"] for n in range(1, 5) if inst[f"part{n}"]]
                print(f"      [{inst['model']} · {inst['pollutant']}]  SN: {inst['serial_number']}")
                if inst["installed_date"]:
                    print(f"        Installed : {inst['installed_date']}")
                if inst["cal_high_date"]:
                    print(f"        Cal. high : {inst['cal_high_date']}")
                if inst["cal_low_date"]:
                    print(f"        Cal. low  : {inst['cal_low_date']}")
                if parts:
                    print(f"        Parts     : {', '.join(parts)}")
                if inst["notes"]:
                    print(f"        Notes     : {inst['notes']}")
        print()


# ── main menu ──────────────────────────────────────────────────────────────────

MENU = [
    ("Overview (all locations → stations → instruments)", overview),
    # ── locations ──
    ("List locations",                     list_locations),
    ("Add location",                       add_location),
    ("Edit location",                      edit_location),
    ("Remove location",                    remove_location),
    # ── stations ──
    ("List stations",                      list_stations),
    ("Add station",                        add_station),
    ("Edit station",                       edit_station),
    ("Remove station",                     remove_station),
    # ── instruments ──
    ("List instruments (detail view)",     list_instruments),
    ("Add instrument",                     add_instrument),
    ("Edit instrument",                    edit_instrument),
    ("Move instrument to another station", move_instrument),
]


def main():
    conn = connect()
    print("\nEnvironmental Instruments Database")
    while True:
        hr()
        for i, (label, _) in enumerate(MENU, 1):
            print(f"  {i}. {label}")
        print("  0. Quit")
        raw = input("\n> ").strip()
        if raw == "0":
            print("Bye.")
            sys.exit(0)
        if raw.isdigit() and 1 <= int(raw) <= len(MENU):
            MENU[int(raw) - 1][1](conn)
        else:
            print("  Invalid choice.")


if __name__ == "__main__":
    main()
