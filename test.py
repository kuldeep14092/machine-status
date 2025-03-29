import cv2
import numpy as np
import time
import mysql.connector
import tkinter as tk
from tkinter import messagebox
from threading import Thread
import json
import os

REGION_FILE = "regions.json"
processing_active = False

def connect_to_db():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="machine_status"
        )
    except mysql.connector.Error as err:
        messagebox.showerror("Database Error", f"Failed to connect to MySQL: {err}")
        return None

def log_to_database(machine_id, camera_id, event_type):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            if event_type == "Machine Stop":
                cursor.execute("INSERT INTO logs (machine_id, camera_id, stop_start_time) VALUES (%s, %s, %s)",
                               (machine_id, camera_id, timestamp))
            elif event_type == "Machine Start":
                cursor.execute("""
                    UPDATE logs 
                    SET stop_end_time = %s 
                    WHERE machine_id = %s AND camera_id = %s AND stop_end_time IS NULL 
                    ORDER BY stop_start_time DESC LIMIT 1""",
                               (timestamp, machine_id, camera_id))
            conn.commit()
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Failed to insert/update data: {err}")

def save_regions(regions):
    with open(REGION_FILE, "w") as file:
        json.dump(regions, file)

def load_regions():
    if os.path.exists(REGION_FILE):
        with open(REGION_FILE, "r") as file:
            return json.load(file)
    return {}

def select_regions(rtsp_url, camera_id):
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        messagebox.showerror("Error", f"Could not open video stream for Camera {camera_id}.")
        return []
    
    ret, frame = cap.read()
    if not ret:
        messagebox.showerror("Error", "Could not read frame from video.")
        return []
    
    regions = []
    while True:
        roi = cv2.selectROI(f"Select ROI - Camera {camera_id}", frame, fromCenter=False, showCrosshair=True)
        if roi != (0, 0, 0, 0):
            regions.append(roi)
        else:
            break
    
    cap.release()
    cv2.destroyAllWindows()
    return regions

def process_video(rtsp_url, machine_id, camera_id, regions):
    global processing_active
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        messagebox.showerror("Error", f"Could not open video stream for Camera {camera_id}.")
        return
    
    region_blinks = {i: {'light_on': False} for i in range(len(regions))}

    while cap.isOpened() and processing_active:
        ret, frame = cap.read()
        if not ret:
            print(f"Lost connection to Camera {camera_id}, retrying...")
            cap.release()
            time.sleep(2)  # Retry delay
            cap = cv2.VideoCapture(rtsp_url)
            continue

        for region_id, (roi_x, roi_y, roi_w, roi_h) in enumerate(regions):
            roi_frame = frame[roi_y:roi_y + roi_h, roi_x:roi_x + roi_w]
            hsv = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2HSV)
            lower_yellow = np.array([20, 100, 100])
            upper_yellow = np.array([40, 255, 255])
            mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
            yellow_intensity = np.sum(cv2.cvtColor(cv2.bitwise_and(roi_frame, roi_frame, mask=mask), cv2.COLOR_BGR2GRAY))
            
            if yellow_intensity > 100 and not region_blinks[region_id]['light_on']:
                region_blinks[region_id]['light_on'] = True
                log_to_database(machine_id, camera_id, "Machine Stop")
            elif yellow_intensity <= 100 and region_blinks[region_id]['light_on']:
                region_blinks[region_id]['light_on'] = False
                log_to_database(machine_id, camera_id, "Machine Start")

            # Determine the machine status
            status_text = "OFF" if region_blinks[region_id]['light_on'] else "ON"
            status_color = (0, 255, 0) if status_text == "ON" else (0, 0, 255)

            # Draw green rectangle around selected regions
            cv2.rectangle(frame, (roi_x, roi_y), (roi_x + roi_w, roi_y + roi_h), (0, 255, 0), 2)
            
            # Display machine number and status above the region
            cv2.putText(frame, f"Machine {region_id} - {status_text}", 
                        (roi_x, roi_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)

        # Show video processing window
        cv2.imshow(f"Camera {camera_id} - Machine {machine_id}", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

def start_processing():
    global processing_active
    processing_active = True
    
    conn = connect_to_db()
    if not conn:
        return
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT machines.id, cameras.id, cameras.rtsp_stream 
        FROM machines 
        JOIN cameras ON machines.camera_id = cameras.id
    """)
    streams = cursor.fetchall()
    cursor.close()
    conn.close()
    
    regions_per_camera = load_regions()
    
    for machine_id, camera_id, rtsp_url in streams:
        if str(camera_id) not in regions_per_camera:
            regions = select_regions(rtsp_url, camera_id)
            regions_per_camera[str(camera_id)] = regions
            save_regions(regions_per_camera)
        else:
            regions = regions_per_camera[str(camera_id)]
        
        thread = Thread(target=process_video, args=(rtsp_url, machine_id, camera_id, regions))
        thread.daemon = True  # Ensure threads close properly when the program exits
        thread.start()

def stop_processing():
    global processing_active
    processing_active = False

def setup_gui():
    root = tk.Tk()
    root.title("Machine Monitoring System")
    root.geometry("300x200")
    
    start_button = tk.Button(root, text="Start Monitoring", command=start_processing)
    start_button.pack(pady=10)
    
    stop_button = tk.Button(root, text="Stop Monitoring", command=stop_processing)
    stop_button.pack(pady=10)
    
    root.mainloop()

if __name__ == "__main__":
    setup_gui()
