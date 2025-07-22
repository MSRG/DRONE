import numpy as np
import logging
from drone.core.models import DroneGaussianProcess, select_ucb_action

logger = logging.getLogger(__name__)

class PrivateCloudBandit:
    def __init__(self, action_space, resource_limit, initial_safe_set=None, exploration_duration=10, 
                 confidence_level=0.1, sliding_window_size=30, gp_hyperparams=None):
        self.action_space = action_space
        self.resource_limit = resource_limit
        self.exploration_duration = exploration_duration
        self.confidence_level = confidence_level
        self.t = 1
        self.exploration_phase = True
        gp_params = gp_hyperparams or {}
        self.performance_gp = DroneGaussianProcess(sliding_window_size=sliding_window_size, **gp_params)
        self.resource_gp = DroneGaussianProcess(sliding_window_size=sliding_window_size, **gp_params)
        if initial_safe_set is None:
            safe_size = max(1, int(len(action_space) * 0.25))
            self.safe_set = action_space[:safe_size].copy()
        else:
            self.safe_set = initial_safe_set.copy()
        self.history = {'actions': [], 'contexts': [], 'performance': [], 
                        'resource_usage': [], 'safe_set_size': []}

    def get_safe_set(self, context, beta_t=None):
        if self.t <= self.exploration_duration:
            return self.safe_set
        if beta_t is None:
            d = self.action_space.shape[1] + context.shape[0]
            from drone.core.models import ucb_beta
            beta_t = ucb_beta(self.t, d)
        inputs = np.array([np.concatenate([action, context]) for action in self.action_space])
        mean, std = self.resource_gp.predict(inputs)
        lcb_values = mean - np.sqrt(beta_t) * std
        safe_indices = np.where(lcb_values <= self.resource_limit)[0]
        if len(safe_indices) == 0:
            logger.warning("No safe actions found. Using current safe set.")
            return self.safe_set
        self.safe_set = self.action_space[safe_indices]
        return self.safe_set

    def select_exploration_action(self, context):
        return self.safe_set[np.random.randint(len(self.safe_set))]

    def select_action(self, context):
        if self.t <= self.exploration_duration:
            self.exploration_phase = True
            return self.select_exploration_action(context)
        self.exploration_phase = False
        safe_set = self.get_safe_set(context)
        d = self.action_space.shape[1] + context.shape[0]
        action, _ = select_ucb_action(action_space=safe_set, context=context,
                                      gp_model=self.performance_gp, t=self.t, d=d, safe_set=None)
        return action

    def update(self, action, context, performance, resource_usage):
        is_safe = resource_usage <= self.resource_limit
        X = np.array([np.concatenate([action, context])])
        self.performance_gp.update(X, np.array([performance]))
        self.resource_gp.update(X, np.array([resource_usage]))
        self.history['actions'].append(action)
        self.history['contexts'].append(context)
        self.history['performance'].append(performance)
        self.history['resource_usage'].append(resource_usage)
        self.history['safe_set_size'].append(len(self.safe_set))
        self.t += 1
        return performance, is_safe

    def reset(self):
        self.performance_gp.reset()
        self.resource_gp.reset()
        self.t = 1
        self.exploration_phase = True
        self.history = {'actions': [], 'contexts': [], 'performance': [], 
                        'resource_usage': [], 'safe_set_size': []}
