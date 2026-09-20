from panda3d.core import loadPrcFileData
loadPrcFileData("", "win-size 1280 720")
loadPrcFileData("", "sync-video false")
loadPrcFileData("", "show-frame-rate-meter false")
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
import time
import math
import csv
import statistics


NUMBER_OF_CUBES = 2500
WARMUP_SECONDS = 3
TEST_DURATION = 30

def percentile(data, percent):

    sorted_data = sorted(data)
    index = int((percent / 100) * (len(sorted_data) - 1))

    return sorted_data[index]

class Benchmark(ShowBase):

    def __init__(self):

        ShowBase.__init__(self)
        self.disableMouse()
        self.setBackgroundColor(0.1, 0.1, 0.1)
        self.camLens.setFov(60)
        self.camLens.setNearFar(
            0.1,
            200
        )
        self.camera.setPos(
            0,
            -15,
            0
        )
        cube_model = self.loader.loadModel(
            "models/misc/rgbCube"
        )
        for i in range(NUMBER_OF_CUBES):
            x = (i % 10) - 4.5
            z = ((i // 10) % 5) - 2
            layer = i // 50
            y = 5 + layer * 3
            cube = cube_model.copyTo(self.render)
            cube.setPos(
                x,
                y,
                z
            )
            cube.setScale(0.3)
        self.start_time = time.perf_counter()
        self.last_frame_time = self.start_time
        self.frame_times = []
        self.finished = False
        self.taskMgr.add(
            self.update,
            "benchmark-update"
        )

    def calculate_results(self):

        if len(self.frame_times) == 0:
            print("Aucune donnée.")
            return

        frame_times_ms = [
            frame_time * 1000
            for frame_time in self.frame_times
        ]
        average_ms = statistics.mean(
            frame_times_ms
        )
        median_ms = statistics.median(
            frame_times_ms
        )
        p95 = percentile(
            frame_times_ms,
            95
        )
        p99 = percentile(
            frame_times_ms,
            99
        )
        average_fps = 1000 / average_ms

        print("\n================================")
        print("PANDA3D RESULTS")
        print("================================")
        print(
            "Number of cubes:",
            NUMBER_OF_CUBES
        )
        print(
            "Frames measured:",
            len(frame_times_ms)
        )
        print(
            f"Average FPS: {average_fps:.2f}"
        )
        print(
            f"Average frame time: {average_ms:.3f} ms"
        )
        print(
            f"Median frame time: {median_ms:.3f} ms"
        )
        print(
            f"P95 frame time: {p95:.3f} ms"
        )
        print(
            f"P99 frame time: {p99:.3f} ms"
        )
        print("================================\n")

        filename = (
            f"panda3d_{NUMBER_OF_CUBES}_cubes.csv"
        )

        with open(
            filename,
            "w",
            newline=""
        ) as file:

            writer = csv.writer(file)
            writer.writerow([
                "frame",
                "frame_time_ms",
                "fps"
            ])

            for index, frame_time in enumerate(
                frame_times_ms
            ):

                fps = 1000 / frame_time
                writer.writerow([
                    index,
                    frame_time,
                    fps
                ])

        print(
            "Results saved to:",
            filename
        )

    def update(self, task):

        now = time.perf_counter()
        frame_time = (
            now - self.last_frame_time
        )
        self.last_frame_time = now
        elapsed = (
            now - self.start_time
        )
        camera_x = (
            math.sin(elapsed) * 2
        )
        camera_z = (
            math.sin(elapsed * 0.7) * 1
        )
        self.camera.setPos(
            camera_x,
            -15,
            camera_z
        )
        if elapsed >= WARMUP_SECONDS:

            self.frame_times.append(
                frame_time
            )

        if (
            elapsed
            >= WARMUP_SECONDS
            + TEST_DURATION
        ):

            if not self.finished:

                self.finished = True
                self.calculate_results()
                self.userExit()

            return Task.done

        return Task.cont

app = Benchmark()

app.run()