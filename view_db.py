import sqlite3
import cv2
import numpy as np
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

try:
    # Connect to the SQLite database
    conn = sqlite3.connect('face_log.db')
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, timestamp, frame FROM face_log ORDER BY id DESC")
    records = cursor.fetchall()

    logging.info(f"Found {len(records)} records.")

    for record in records:
        id, name, timestamp, frame_bytes = record

        logging.info(f"ID: {id}, Name: {name}, Timestamp: {timestamp}")

        # Convert BLOB to image and display
        try:
            np_arr = np.frombuffer(frame_bytes, dtype=np.uint8)
            image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if image is not None:
                cv2.imshow(f"{name} @ {timestamp}", image)
                key = cv2.waitKey(0)
                if key == ord('q'):
                    logging.info("Quit signal received. Exiting display loop.")
                    break
            else:
                logging.warning(f"Could not decode image for record ID {id}.")
        except Exception as e:
            logging.error(f"Error decoding/displaying image for record ID {id}: {e}")

except sqlite3.Error as e:
    logging.error(f"Database error: {e}")

except Exception as e:
    logging.error(f"Unexpected error: {e}")

finally:
    cv2.destroyAllWindows()
    if 'conn' in locals():
        conn.close()
        logging.info("Database connection closed.")
