from ursina_test import *
from ursina import Ursina, Entity, camera, window, application
import time
import math
import csv
import statistics

NUMBER_OF_CUBES = 2500
WARMUP_SECONDS = 3
TEST_DURATION = 30

app = Ursina()

window.title = "Ursina Benchmark"
window.borderless = False
window.fullscreen = False
window.vsync = False

for i in range(NUMBER_OF_CUBES):

    x = (i % 10) - 4.5
    y = ((i // 10) % 5) - 2
    layer = i // 50
    z = 5 + layer * 3

    Entity(
        model='cube',
        position=(x, y, z),
        scale=0.6
    )

camera.position = (0, 0, -15)
camera.fov = 60

start_time = time.perf_counter()
last_frame_time = start_time

frame_times = []

def percentile(data, percent):
    sorted_data = sorted(data)
    index = int((percent / 100) * (len(sorted_data) - 1))

    return sorted_data[index]

def calculate_results():

    if len(frame_times) == 0:
        print("Aucune donnée enregistrée.")
        return

    frame_times_ms = [
        frame_time * 1000
        for frame_time in frame_times
    ]

    average_ms = statistics.mean(frame_times_ms)
    median_ms = statistics.median(frame_times_ms)

    p95 = percentile(frame_times_ms, 95)
    p99 = percentile(frame_times_ms, 99)

    average_fps = 1000 / average_ms

    print("\n================================")
    print("URSINA RESULTS")
    print("================================")
    print("Number of cubes:", NUMBER_OF_CUBES)
    print("Frames measured:", len(frame_times_ms))
    print(f"Average FPS: {average_fps:.2f}")
    print(f"Average frame time: {average_ms:.3f} ms")
    print(f"Median frame time: {median_ms:.3f} ms")
    print(f"P95 frame time: {p95:.3f} ms")
    print(f"P99 frame time: {p99:.3f} ms")
    print("================================\n")

    filename = f"ursina_{NUMBER_OF_CUBES}_cubes.csv"

    with open(filename, "w", newline="") as file:

        writer = csv.writer(file)

        writer.writerow([
            "frame",
            "frame_time_ms",
            "fps"
        ])

        for index, frame_time in enumerate(frame_times_ms):

            fps = 1000 / frame_time
            writer.writerow([
                index,
                frame_time,
                fps
            ])

    print("Results saved to:", filename)

def update():

    global last_frame_time

    now = time.perf_counter()
    frame_time = now - last_frame_time
    last_frame_time = now
    elapsed = now - start_time

    camera.x = math.sin(elapsed) * 2
    camera.y = math.sin(elapsed * 0.7) * 1

    if elapsed >= WARMUP_SECONDS:

        frame_times.append(frame_time)

    if elapsed >= WARMUP_SECONDS + TEST_DURATION:

        calculate_results()

        application.quit()

app.run()