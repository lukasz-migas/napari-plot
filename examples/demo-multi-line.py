"""Demo example.

Taken and adapted from:
https://www.python-graph-gallery.com/web-multiple-lines-and-panels
"""
from functools import reduce

import matplotlib.cm as cm
import numpy as np
from scipy.special import expit
import napari_plot


class Probabilities:
    """Probabilities instance"""

    def __init__(self, grid, auth, responses, programs):
        self.grid = grid
        self.auth = auth
        self.responses = responses
        self.programs = programs

    def compute(self, j):
        """Compute values."""
        eta = self.grid * self._auth_coef() + self._program_coef(j)
        n_responses = len(self.responses["mean"]) + 1
        probs = [0] * n_responses
        for i in range(n_responses):
            if i == 0:
                response = self._response_coef(i)
                probs[i] = expit(response - eta)
            elif i < n_responses - 1:
                response = self._response_coef(i)
                response_previous = self._response_coef(i - 1)
                probs[i] = expit(response - eta) - expit(response_previous - eta)
            else:
                probs[i] = 1 - reduce(lambda a, b: a + b, probs[:-1])

        return probs

    def _auth_coef(self):
        mean = self.auth["mean"]
        sd = self.auth["sd"]
        return np.random.normal(mean, sd)

    def _response_coef(self, idx):
        mean = self.responses["mean"][idx]
        sd = self.responses["sd"][idx]
        return np.random.normal(mean, sd)

    def _program_coef(self, idx):
        mean = self.programs["mean"][idx]
        sd = self.programs["sd"][idx]
        return np.random.normal(mean, sd)


x = np.linspace(-3, 3, 500)

colormap = cm.get_cmap("plasma")
COLORS = [colormap(x) for x in np.linspace(0.8, 0.15, num=4)]
LABELS = ["Not common at all", "Not very common", "Somewhat common", "Very common"]
AUTH = {"mean": 0.21, "sd": 0.06}
RESPONSE = {"mean": [-0.71, 0.5, 1.28], "sd": [0.05] * 3}
PROGRAMS = {"mean": [0, 0.23, 0.39, 0.69, 0.97], "sd": [0] + [0.09] * 4}

# initialize the probabilities instance
probabilities = Probabilities(x, AUTH, RESPONSE, PROGRAMS)
# define your desired colors

ys = {0: [], 1: [], 2: [], 3: []}
for _ in range(100):
    probs = probabilities.compute(0)
    for i, y in enumerate(probs):
        ys[i].append(y)

viewer = napari_plot.Viewer()
for i, _ys in enumerate(ys.values()):
    viewer.add_multi_line({"x": x, "ys": _ys}, color=COLORS[i], opacity=0.4, width=1, name=LABELS[i])
viewer.reset_view()
viewer.axis.x_label = ""
viewer.axis.y_label = ""
napari_plot.run()
