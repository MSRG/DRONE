import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern

class DroneGaussianProcess:
    def __init__(self,
                 length_scale=1.0,
                 length_scale_bounds=(1e-5, 1e5),
                 nu=1.5,
                 alpha=1e-2,
                 normalize_y=True,
                 n_restarts_optimizer=5,
                 sliding_window_size=30):
        self.kernel = Matern(length_scale=length_scale,
                             length_scale_bounds=length_scale_bounds,
                             nu=nu)
        self.model = GaussianProcessRegressor(
            kernel=self.kernel,
            alpha=alpha,
            normalize_y=normalize_y,
            n_restarts_optimizer=n_restarts_optimizer
        )
        self.X = None
        self.y = None
        self.sliding_window_size = sliding_window_size
        self.X_mean = None
        self.X_std = None

    def update(self, X, y):
        if self.X is None:
            self.X = X
            self.y = y
        else:
            self.X = np.vstack((self.X, X))
            self.y = np.append(self.y, y)

        if len(self.y) > self.sliding_window_size:
            self.X = self.X[-self.sliding_window_size:]
            self.y = self.y[-self.sliding_window_size:]

        self.X_mean = np.mean(self.X, axis=0)
        self.X_std = np.std(self.X, axis=0) + 1e-8
        X_normalized = (self.X - self.X_mean) / self.X_std
        self.model.fit(X_normalized, self.y)

    def predict(self, X):
        if self.X is None or len(self.X) == 0:
            prior_variance = np.diag(self.kernel(X, X))
            return np.zeros(X.shape[0]), np.sqrt(prior_variance)
        X_normalized = (X - self.X_mean) / self.X_std
        mean, std = self.model.predict(X_normalized, return_std=True)
        return mean, std

    def get_data(self):
        return self.X.copy() if self.X is not None else None, self.y.copy() if self.y is not None else None

    def reset(self):
        self.X = None
        self.y = None
