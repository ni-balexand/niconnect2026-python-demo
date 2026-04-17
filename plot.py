import matplotlib.pyplot as plt
from matplotlib import ticker
import numpy as np

class Plotter:
    def __init__(self, sample_rate, num_samples):
        delta_t = 1.0 / sample_rate
        waveform_t = num_samples * delta_t
        lines = []

        blank_wfm = np.zeros(num_samples)
        plt.style.use("dark_background")
        fig, axs = plt.subplots(2)
        x_range = np.arange(0.0, waveform_t, delta_t)
        for ax in axs:
            ax.set_xlim(0, waveform_t)
            ax.set_ylim(-0.6, 0.6)
            ax.xaxis.set_major_formatter(ticker.StrMethodFormatter("{x:.3g}"))
            ax.grid(True, alpha=0.3)
            lines += ax.plot(x_range, blank_wfm, "sg-", x_range, blank_wfm, "m-", animated=True)
            ax.legend(["Ch0", "Ch1"], loc="lower left")
        axs[0].set_title("Record 0")
        axs[1].set_title("Record 1")
        plt.tight_layout()
        plt.show(block=False)
        plt.pause(1/30)
        print("Press the Q key to close the plot")
        bg = fig.canvas.copy_from_bbox(fig.bbox)

        self.fig = fig
        self.axs = axs
        self.lines = lines
        self.bg = bg

    def is_open(self):
        return plt.fignum_exists(self.fig.number)

    def update_plot(self, data_sources):
        for line, data_source in zip(self.lines, data_sources):
            line.set_ydata(data_source)
        self.fig.canvas.restore_region(self.bg)
        self.axs[0].draw_artist(self.lines[0])
        self.axs[0].draw_artist(self.lines[1])
        self.axs[1].draw_artist(self.lines[2])
        self.axs[1].draw_artist(self.lines[3])

        self.fig.canvas.blit(self.fig.bbox)
        plt.pause(0.001)
