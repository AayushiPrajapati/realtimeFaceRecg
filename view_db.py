import sqlite3
import cv2
import numpy as np

# Connect to the SQLite database
conn = sqlite3.connect('face_log.db')
cursor = conn.cursor()

# Fetch all records
cursor.execute("SELECT id, name, timestamp, frame FROM face_log ORDER BY id DESC")
records = cursor.fetchall()

print(f"Found {len(records)} records.")

for record in records:
    id, name, timestamp, frame_bytes = record

    print(f"\nID: {id}")
    print(f"Name: {name}")
    print(f"Timestamp: {timestamp}")

    # Convert BLOB to image and display
    np_arr = np.frombuffer(frame_bytes, dtype=np.uint8)
    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if image is not None:
        cv2.imshow(f"{name} @ {timestamp}", image)
        key = cv2.waitKey(0)
        if key == ord('q'):
            break
    else:
        print("Could not decode image from database.")

cv2.destroyAllWindows()
conn.close()
