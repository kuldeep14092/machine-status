import cv2
import numpy as np
import time
import mysql.connector
import tkinter as tk
from tkinter import filedialog, messagebox
from threading import Thread
import socket
import json
import os

# File to store saved region selections
REGION_FILE = "regions.json"

# Get machine name
machine_name = socket.gethostname()

# Function to connect to MySQL
def connect_to_db():
    try:
        conn = mysql.connector.connect(
            host="localhost",      # Change to your MySQL host
            user="root",           # Your MySQL username
            password="",           # Your MySQL password
            database="status"      # Your MySQL database name
        )
        return conn
    except mysql.connector.Error as err:
        messagebox.showerror("Database Error", f"Failed to connect to MySQL: {err}")
        return None

# Function to insert blink data into MySQL
def log_to_database(region_id, event_type, timestamp):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            query = "INSERT INTO blink_logs (region_id, event_type, timestamp) VALUES (%s, %s, %s)"
            cursor.execute(query, (region_id, event_type, timestamp))
            conn.commit()
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Failed to insert data: {err}")

# Function to get the current timestamp
def get_timestamp():
    return time.strftime('%Y-%m-%d %H:%M:%S')

# Function to save selected regions to a file
def save_regions(video_path, regions):
    with open(REGION_FILE, "w") as file:
        json.dump({"video_path": video_path, "regions": regions}, file)

# Function to load saved regions
def load_regions():
    if os.path.exists(REGION_FILE):
        with open(REGION_FILE, "r") as file:
            return json.load(file)
    return None

# Function to process video and detect blinks
def run_video_processing(video_path, regions=None):
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        messagebox.showerror("Error", "Could not open video or RTSP stream.")
        return

    ret, frame = cap.read()
    if not ret:
        messagebox.showerror("Error", "Could not read the first frame.")
        return

    # If no regions provided, let user select regions
    if regions is None:
        regions = []
        while True:
            roi = cv2.selectROI("Select ROI", frame, fromCenter=False, showCrosshair=True)
            if roi != (0, 0, 0, 0):  
                regions.append(roi)
            else:
                break
        cv2.destroyWindow("Select ROI")
        save_regions(video_path, regions)  # Save regions

    # Initialize tracking for blinks in each region
    region_blinks = {i: {'light_on': False, 'start_time': None} for i in range(1, len(regions) + 1)}

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        for i, roi in enumerate(regions, 1):
            roi_x, roi_y, roi_w, roi_h = roi
            roi_frame = frame[roi_y:roi_y+roi_h, roi_x:roi_x+roi_w]

            # Convert ROI to HSV color space
            hsv = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2HSV)

            # Define yellow color range for detection
            lower_yellow = np.array([20, 100, 100])
            upper_yellow = np.array([40, 255, 255])
            mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
            yellow_area = cv2.bitwise_and(roi_frame, roi_frame, mask=mask)

            # Convert to grayscale and calculate intensity
            gray_yellow = cv2.cvtColor(yellow_area, cv2.COLOR_BGR2GRAY)
            yellow_intensity = np.sum(gray_yellow)

            # Detect if light is on or off based on intensity threshold
            if yellow_intensity > 100:
                if not region_blinks[i]['light_on']:
                    region_blinks[i]['light_on'] = True
                    region_blinks[i]['start_time'] = get_timestamp()
                    log_to_database(i, "Machine Start", region_blinks[i]['start_time'])
            else:
                if region_blinks[i]['light_on']:
                    region_blinks[i]['light_on'] = False
                    blink_end_time = get_timestamp()
                    log_to_database(i, "Machine End", blink_end_time)

            # Draw bounding boxes on the video
            cv2.rectangle(frame, (roi_x, roi_y), (roi_x + roi_w, roi_y + roi_h), (0, 255, 0), 2)
            cv2.putText(frame, f"Region {i}", (roi_x, roi_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Display the video frame with bounding boxes
        cv2.putText(frame, "Press 'q' to Quit", (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.imshow("Frame", frame)

        # Press 'q' to exit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# Function to start the processing in a separate thread
def start_processing(new_session=False):
    video_path = video_entry.get()
    if video_path == "":
        messagebox.showerror("Error", "Please provide a valid video path or RTSP stream URL.")
        return

    if new_session:
        processing_thread = Thread(target=run_video_processing, args=(video_path, None))
    else:
        saved_data = load_regions()
        if saved_data and saved_data["video_path"] == video_path:
            processing_thread = Thread(target=run_video_processing, args=(video_path, saved_data["regions"]))
        else:
            messagebox.showerror("Error", "No saved regions found for this video. Please select new regions.")
            return

    processing_thread.start()

# GUI Setup
root = tk.Tk()
root.title("Blink Detection")

video_label = tk.Label(root, text="Enter Video Path (or RTSP URL):")
video_label.pack(pady=10)

video_entry = tk.Entry(root, width=50)
video_entry.pack(pady=10)

def browse_video():
    video_path = filedialog.askopenfilename(filetypes=[("MP4 Files", "*.mp4"), ("All Files", "*.*")])
    if video_path:
        video_entry.delete(0, tk.END)
        video_entry.insert(0, video_path)

browse_button = tk.Button(root, text="Browse", command=browse_video)
browse_button.pack(pady=10)

start_button = tk.Button(root, text="Start New", command=lambda: start_processing(new_session=True))
start_button.pack(pady=10)

resume_button = tk.Button(root, text="Resume", command=lambda: start_processing(new_session=False))
resume_button.pack(pady=10)

root.mainloop()
