"""Mark the baseline, peak, and integration window of a synthetic signal."""

import numpy as np

import napari_plot

time = np.linspace(0, 10, 300)
signal = 0.15 + np.exp(-0.5 * ((time - 6) / 0.65) ** 2)
samples = np.array([5.4, 6.0, 6.6])
sample_signal = 0.15 + np.exp(-0.5 * ((samples - 6) / 0.65) ** 2)

viewer = napari_plot.Viewer(title="Marking a signal peak")
viewer.axhspan(0.12, 0.18, color="gray", opacity=0.3, name="Baseline band")
viewer.axvspan(5.4, 6.6, color="steelblue", opacity=0.2, name="Integration window")
viewer.fill_betweenx([0.24, 0.33, 0.48], [1.2, 1.0, 1.2], [2.2, 2.7, 2.2], color="plum", name="Side band")
viewer.axhline(0.15, color="gray", line_style="dotted", name="Baseline")
viewer.axvline(6, color="orange", line_style="dashed", name="Peak time")
viewer.stem(samples, sample_signal, baseline=0.15, color="steelblue", name="Samples")
viewer.plot(time, signal, color="cyan", name="Signal")
viewer.rectangle((5.6, 0.87), 0.8, 0.32, color="orange", name="Peak bounds")
viewer.text(0.6, 0.21, "Baseline", color="white", alignment="left")
viewer.annotate("Peak", xy=(6, 1.15), xytext=(7.4, 1.3), color="orange", alignment="left", offset=(0.08, 0.02))
viewer.axis.x_label = "Time (s)"
viewer.axis.y_label = "Signal (a.u.)"
viewer.margins = (0.04, 0.08)
viewer.reset_view()

if __name__ == "__main__":
    napari_plot.run()
