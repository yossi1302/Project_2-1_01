import moderngl
import moderngl_window as mglw
import numpy as np
from pyrr import Matrix44
import time
import math
import csv
import statistics

NUMBER_OF_CUBES = 2500
WARMUP_SECONDS = 3
TEST_DURATION = 30

def percentile(data, percent):

    sorted_data = sorted(data)

    index = int(
        (percent / 100)
        * (len(sorted_data) - 1)
    )

    return sorted_data[index]

class Benchmark(mglw.WindowConfig):

    gl_version = (3, 3)
    title = "ModernGL Benchmark"
    window_size = (
        1280,
        720
    )
    aspect_ratio = (
        1280 / 720
    )
    resizable = False

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        self.ctx.enable(
            moderngl.DEPTH_TEST
        )

        self.program = self.ctx.program(

            vertex_shader="""

                #version 330

                uniform mat4 projection;
                uniform mat4 view;
                uniform mat4 model;

                in vec3 in_position;

                out vec3 v_position;

                void main()
                {
                    v_position = in_position;

                    gl_Position =
                        projection
                        * view
                        * model
                        * vec4(
                            in_position,
                            1.0
                        );
                }

            """,

            fragment_shader="""

                #version 330

                in vec3 v_position;

                out vec4 fragColor;

                void main()
                {
                    vec3 color =
                        vec3(
                            0.4,
                            0.7,
                            0.9
                        );

                    fragColor =
                        vec4(
                            color,
                            1.0
                        );
                }

            """
        )

        self.cube = (
            mglw.geometry.cube(
                size=(0.6, 0.6, 0.6)
            )
        )

        self.cube_positions = []


        for i in range(NUMBER_OF_CUBES):

            x = (
                (i % 10)
                - 4.5
            )

            y = (
                ((i // 10) % 5)
                - 2
            )

            layer = i // 50

            z = (
                -5
                - layer * 3
            )

            self.cube_positions.append(
                (
                    x,
                    y,
                    z
                )
            )

        projection = (
            Matrix44.perspective_projection(
                60,
                self.aspect_ratio,
                0.1,
                200
            )
        )

        self.program[
            "projection"
        ].write(

            projection.astype(
                "f4"
            ).tobytes()
        )

        self.start_time = (
            time.perf_counter()
        )
        self.last_frame_time = (
            self.start_time
        )
        self.frame_times = []
        self.finished = False

    def calculate_results(self):

        if len(self.frame_times) == 0:

            print("Aucune donnée.")

            return

        frame_times_ms = [

            value * 1000

            for value in self.frame_times
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
        average_fps = (
            1000 / average_ms
        )

        print("\n================================")
        print("MODERNGL RESULTS")
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
            f"moderngl_{NUMBER_OF_CUBES}_cubes.csv"
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

            for index, value in enumerate(
                frame_times_ms
            ):
                fps = (
                    1000 / value
                )
                writer.writerow([
                    index,
                    value,
                    fps
                ])

        print(
            "Results saved to:",
            filename
        )

    def on_render(self, time_value, frame_time):

        now = time.perf_counter()

        measured_frame_time = (
            now - self.last_frame_time
        )
        self.last_frame_time = now
        elapsed = (
            now - self.start_time
        )

        self.ctx.clear(
            0.1,
            0.1,
            0.1
        )

        camera_x = (
            math.sin(elapsed) * 2
        )
        camera_y = (
            math.sin(
                elapsed * 0.7
            ) * 1
        )

        view = Matrix44.from_translation(
            (
                -camera_x,
                -camera_y,
                -5
            )
        )

        self.program[
            "view"
        ].write(

            view.astype(
                "f4"
            ).tobytes()
        )

        for position in self.cube_positions:

            model = (
                Matrix44.from_translation(
                    position
                )
            )

            self.program[
                "model"
            ].write(

                model.astype(
                    "f4"
                ).tobytes()
            )
            self.cube.render(
                self.program
            )

        if elapsed >= WARMUP_SECONDS:

            self.frame_times.append(
                measured_frame_time
            )

        if (
            elapsed
            >= WARMUP_SECONDS
            + TEST_DURATION
        ):

            if not self.finished:

                self.finished = True

                self.calculate_results()

                self.wnd.close()

if __name__ == "__main__":

    mglw.run_window_config(
        Benchmark
    )