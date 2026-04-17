import time

class Profiler:
    def __init__(self):
        self.time_last = time.perf_counter()
        self.frame = 0

    def tick(self):
        self.frame += 1
        if self.frame % 100 == 0:
            time_now = time.perf_counter()
            fps = 100 / (time_now - self.time_last)
            print(f"{fps} fps")
            self.time_last = time_now
