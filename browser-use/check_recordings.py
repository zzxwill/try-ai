#!/usr/bin/env python3
"""
Script to check for Playwright recordings and display information.
"""

import os
import sys
from datetime import datetime

def main():
    videos_dir = "videos"
    
    if not os.path.exists(videos_dir):
        print(f"❌ Videos directory '{videos_dir}' does not exist!")
        return 1
    
    recording_dirs = [d for d in os.listdir(videos_dir) if d.startswith("recording-")]
    
    if not recording_dirs:
        print(f"❌ No recording directories found in '{videos_dir}'!")
        return 1
    
    print(f"Found {len(recording_dirs)} recording directories:")
    
    for recording_dir in sorted(recording_dirs, reverse=True):
        dir_path = os.path.join(videos_dir, recording_dir)
        
        # Extract timestamp from directory name
        try:
            timestamp_str = recording_dir.split("-", 1)[1]
            timestamp = datetime.strptime(timestamp_str, "%Y%m%d-%H%M%S")
            date_formatted = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        except:
            date_formatted = "Unknown date"
        
        video_files = [f for f in os.listdir(dir_path) if f.endswith(".webm")]
        
        print(f"\n📁 {recording_dir} ({date_formatted}):")
        
        if not video_files:
            print("  ❌ No video files found!")
            continue
        
        for video_file in video_files:
            video_path = os.path.join(dir_path, video_file)
            size_bytes = os.path.getsize(video_path)
            
            if size_bytes < 1024:
                size_str = f"{size_bytes} bytes"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes/1024:.2f} KB"
            else:
                size_str = f"{size_bytes/(1024*1024):.2f} MB"
                
            print(f"  🎬 {video_file} ({size_str})")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 