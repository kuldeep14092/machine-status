import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from test import start_processing, stop_processing

def connect_to_db():
    return mysql.connector.connect(host="localhost", user="root", password="", database="machine_status")

def add_units():
    def submit_units():
        unit_names = unit_entry.get("1.0", tk.END).strip().split("\n")
        conn = connect_to_db()
        cursor = conn.cursor()
        for unit_name in unit_names:
            if unit_name:
                cursor.execute("INSERT INTO unit (unit_name) VALUES (%s) ON DUPLICATE KEY UPDATE unit_name=unit_name", (unit_name,))
        conn.commit()
        cursor.close()
        conn.close()
        messagebox.showinfo("Success", "Units added successfully!")
        unit_window.destroy()
    
    unit_window = tk.Toplevel(root)
    unit_window.title("Add Units")
    tk.Label(unit_window, text="Enter Unit Names (one per line):").pack(pady=5)
    unit_entry = tk.Text(unit_window, height=5, width=30)
    unit_entry.pack(pady=5)
    tk.Button(unit_window, text="Submit", command=submit_units).pack(pady=5)

def add_cameras():
    def fetch_units():
        conn = connect_to_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, unit_name FROM unit")
        units = {row[1]: row[0] for row in cursor.fetchall()}
        cursor.close()
        conn.close()
        return units

    def submit_cameras():
        camera_name = camera_entry.get().strip()
        unit_name = unit_var.get().strip()
        rtsp_stream = rtsp_entry.get().strip()
        units = fetch_units()
        unit_id = units.get(unit_name)
        
        if camera_name and unit_id and rtsp_stream:
            conn = connect_to_db()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO cameras (camera_name, unit_id, rtsp_stream) VALUES (%s, %s, %s)", (camera_name, unit_id, rtsp_stream))
            conn.commit()
            cursor.close()
            conn.close()
            messagebox.showinfo("Success", "Camera added successfully!")
            camera_window.destroy()
        else:
            messagebox.showerror("Error", "All fields are required!")

    camera_window = tk.Toplevel(root)
    camera_window.title("Add Cameras")
    tk.Label(camera_window, text="Camera Name:").pack()
    camera_entry = tk.Entry(camera_window)
    camera_entry.pack()
    tk.Label(camera_window, text="Select Unit:").pack()
    unit_var = tk.StringVar()
    unit_dropdown = ttk.Combobox(camera_window, textvariable=unit_var, values=list(fetch_units().keys()))
    unit_dropdown.pack()
    tk.Label(camera_window, text="RTSP Stream URL:").pack()
    rtsp_entry = tk.Entry(camera_window)
    rtsp_entry.pack()
    tk.Button(camera_window, text="Submit", command=submit_cameras).pack(pady=5)

def add_machines():
    def fetch_cameras():
        conn = connect_to_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, camera_name FROM cameras")
        cameras = {row[1]: row[0] for row in cursor.fetchall()}
        cursor.close()
        conn.close()
        return cameras

    def submit_machines():
        machine_name = machine_entry.get().strip()
        camera_name = camera_var.get()
        cameras = fetch_cameras()
        camera_id = cameras.get(camera_name)
        
        if machine_name and camera_id:
            conn = connect_to_db()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO machines (machine_name, camera_id) VALUES (%s, %s)", (machine_name, camera_id))
            conn.commit()
            cursor.close()
            conn.close()
            messagebox.showinfo("Success", "Machine added successfully!")
            machine_window.destroy()
        else:
            messagebox.showerror("Error", "All fields are required!")

    machine_window = tk.Toplevel(root)
    machine_window.title("Add Machines")
    tk.Label(machine_window, text="Machine Name:").pack()
    machine_entry = tk.Entry(machine_window)
    machine_entry.pack()
    tk.Label(machine_window, text="Select Camera:").pack()
    camera_var = tk.StringVar()
    camera_dropdown = ttk.Combobox(machine_window, textvariable=camera_var, values=list(fetch_cameras().keys()))
    camera_dropdown.pack()
    tk.Button(machine_window, text="Submit", command=submit_machines).pack(pady=5)

# def start_process():
#     conn = connect_to_db()
#     cursor = conn.cursor()
#     cursor.execute("INSERT INTO process_log (status) VALUES ('Started')")
#     conn.commit()
#     cursor.close()
#     conn.close()
#     messagebox.showinfo("Success", "Process started successfully!")

# def stop_process():
#     conn = connect_to_db()
#     cursor = conn.cursor()
#     cursor.execute("INSERT INTO process_log (status) VALUES ('Stopped')")
#     conn.commit()
#     cursor.close()
#     conn.close()
#     messagebox.showinfo("Success", "Process stopped successfully!")

def start_process():
    start_processing()  # Start processing function from test.py
    messagebox.showinfo("Success", "Process started successfully!")

def stop_process():
    stop_processing()  # Stop processing function from test.py
    messagebox.showinfo("Success", "Process stopped successfully!")

# Main GUI Setup
root = tk.Tk()
root.title("Machine Management System")
root.geometry("300x300")

unit_button = tk.Button(root, text="Add Units", command=add_units)
unit_button.pack(pady=5)

camera_button = tk.Button(root, text="Add Cameras", command=add_cameras)
camera_button.pack(pady=5)

machine_button = tk.Button(root, text="Add Machines", command=add_machines)
machine_button.pack(pady=5)

start_button = tk.Button(root, text="Start Process", command=start_process, bg="green", fg="white")
start_button.pack(pady=5)

stop_button = tk.Button(root, text="Stop Process", command=stop_process, bg="red", fg="white")
stop_button.pack(pady=5)

root.mainloop()
