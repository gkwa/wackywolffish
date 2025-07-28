#!/usr/bin/env python3

import re
import time
import sys
import datetime

PROGRESS_FILE = "ffmpeg_progress.log"
TOTAL_FRAMES = 1997

def parse_progress():
   """Parse the latest progress from ffmpeg output"""
   try:
       with open(PROGRESS_FILE, 'r') as f:
           content = f.read()
       
       # Find the last frame number
       frame_matches = re.findall(r'frame=(\d+)', content)
       if not frame_matches:
           return None
       
       current_frame = int(frame_matches[-1])
       
       # Find the last fps value
       fps_matches = re.findall(r'fps=([\d.]+)', content)
       if not fps_matches:
           return None
           
       current_fps = float(fps_matches[-1])
       
       # Find the last speed value
       speed_matches = re.findall(r'speed=([\d.]+)x', content)
       speed = float(speed_matches[-1]) if speed_matches else None
       
       return {
           'frame': current_frame,
           'fps': current_fps,
           'speed': speed,
           'progress_percent': (current_frame / TOTAL_FRAMES) * 100
       }
       
   except (FileNotFoundError, ValueError, IndexError) as e:
       return None

def format_time(seconds):
   """Format seconds into human readable time"""
   if seconds < 60:
       return f"{seconds:.0f}s"
   elif seconds < 3600:
       minutes = seconds // 60
       secs = seconds % 60
       return f"{minutes:.0f}m {secs:.0f}s"
   else:
       hours = seconds // 3600
       minutes = (seconds % 3600) // 60
       return f"{hours:.0f}h {minutes:.0f}m"

def main():
   print("FFmpeg Progress Monitor")
   print("======================")
   print(f"Total frames to process: {TOTAL_FRAMES}")
   print("Press Ctrl+C to stop monitoring\n")
   
   try:
       while True:
           progress = parse_progress()
           
           if progress:
               remaining_frames = TOTAL_FRAMES - progress['frame']
               
               if progress['fps'] > 0:
                   time_remaining = remaining_frames / progress['fps']
                   eta = datetime.datetime.now() + datetime.timedelta(seconds=time_remaining)
                   
                   print(f"\rFrame: {progress['frame']:4d}/{TOTAL_FRAMES} "
                         f"({progress['progress_percent']:5.1f}%) | "
                         f"Speed: {progress['fps']:4.1f} fps | "
                         f"Remaining: {format_time(time_remaining)} | "
                         f"ETA: {eta.strftime('%H:%M:%S')}", end="", flush=True)
               else:
                   print(f"\rFrame: {progress['frame']:4d}/{TOTAL_FRAMES} "
                         f"({progress['progress_percent']:5.1f}%) | "
                         f"Calculating...", end="", flush=True)
           else:
               print(f"\rWaiting for progress data...", end="", flush=True)
           
           time.sleep(2)
           
   except KeyboardInterrupt:
       print(f"\n\nMonitoring stopped.")
   except Exception as e:
       print(f"\nError: {e}")

if __name__ == "__main__":
   main()
