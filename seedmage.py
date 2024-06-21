#!/usr/bin/env python3
'''
Fake torrent seeder
'''

import argparse
import random
import time
import sys
import signal
import requests
import threading
import glob
import concurrent.futures

import torrent
import utils

def print_success(text):
    print("\033[32m" + text + "\033[0m")

def print_error(text):
    print("\033[31m" + text + "\033[0m")

def signal_handler(sig, frame):
    print_error("\nClosing SeedMage right now! wait next cycle")
    stop_event.set()  # Set the event to stop the printer thread

print(r'''
            .
           /:\
          /;:.\
         //;:. \     SEEDMAGE
        ///;:.. \
  __--"////;:... \"--__
--__   "--_____--"   __--
    """--_______--"""
''')

parser = argparse.ArgumentParser()
parser.add_argument("upload_speed", help="Upload speed in kB/s", type=int)
parser.add_argument("--update-interval", help="Upload interval in seconds", type=int)
args = parser.parse_args()

#signal.signal(signal.SIGINT, signal_handler)

def torrent_exec(path, total_uploaded, lock, stop_event):
    # Torrent general information
    torrent_file = torrent.File(path)

    # Requesting seeder information to the tracker
    seeder = torrent.Seeder(torrent_file)
    while True:
        try:
            seeder.load_peers()
            break
        except requests.exceptions.Timeout:
            print_error("timeout")

    # Calculate a few parameters
    seed_per_second = args.upload_speed * 1024
    update_interval = args.update_interval
    total_up = 0
    # Seeding
    while not stop_event.is_set():
        time.sleep(update_interval)
        uploaded_bytes = seed_per_second * update_interval
        uploaded_bytes = int(uploaded_bytes * random.uniform(0.8, 1.2))  # +- 20%

        with lock:
            total_uploaded[0] += uploaded_bytes
            total_up += uploaded_bytes

        while True:
            try:
                seeder.upload(total_up)
                break
            except requests.exceptions.Timeout:
                print_error("timeout")

def print_total_uploaded(total_uploaded, lock, stop_event):
    while not stop_event.is_set():
        time.sleep(5)
        with lock:
            print_success(f"Total uploaded: {utils.sizeof_fmt(total_uploaded[0])}")

def main():
  global stop_event
  total_uploaded = [0]
  lock = threading.Lock()
  stop_event = threading.Event()
  signal.signal(signal.SIGINT, signal_handler)
  printer_thread = threading.Thread(target=print_total_uploaded, args=(total_uploaded, lock, stop_event))
  printer_thread.start()
  
  with concurrent.futures.ThreadPoolExecutor() as executor:
      for x in glob.glob('torrent/*.torrent'):
          print(x)
          executor.submit(torrent_exec, x, total_uploaded, lock, stop_event)


  printer_thread.join()

if __name__ == '__main__':
    main()
