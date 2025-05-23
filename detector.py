# app/detector.py
import cv2
import face_recognition

def detect_faces(frame):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    boxes = face_recognition.face_locations(rgb)
    encodings = face_recognition.face_encodings(rgb, boxes)
    return boxes, encodings

def draw_boxes(frame, boxes, names=None):
    for i, (top, right, bottom, left) in enumerate(boxes):
        name = names[i] if names and i < len(names) else "Unseen"
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
    return frame
