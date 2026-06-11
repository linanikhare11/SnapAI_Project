import sqlite3
import os

# Connect to the database
db_path = "snapai.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Query all events
cursor.execute("SELECT id, title, event_type, event_date, slug FROM events")
events = cursor.fetchall()

print("=" * 80)
print("ALL EVENTS IN DATABASE")
print("=" * 80)

if not events:
    print("No events found in the database.")
else:
    print(f"Total events: {len(events)}\n")
    for event in events:
        event_id, title, event_type, event_date, slug = event
        print(f"ID: {event_id}")
        print(f"Title: {title}")
        print(f"Type: {event_type}")
        print(f"Date: {event_date}")
        print(f"Slug: {slug}")
        print("-" * 40)

# Search specifically for Lina's Birthday
print("\n" + "=" * 80)
print("SEARCH FOR 'Lina's Birthday'")
print("=" * 80)

cursor.execute("SELECT id, title, event_type, event_date, slug FROM events WHERE title LIKE ? OR title LIKE ?", ('%Lina%', '%Birthday%'))
lina_events = cursor.fetchall()

if not lina_events:
    print("No events found with 'Lina' or 'Birthday' in the title.")
else:
    print(f"Found {len(lina_events)} matching event(s):\n")
    for event in lina_events:
        event_id, title, event_type, event_date, slug = event
        print(f"ID: {event_id}")
        print(f"Title: {title}")
        print(f"Type: {event_type}")
        print(f"Date: {event_date}")
        print(f"Slug: {slug}")
        print("-" * 40)

conn.close()
