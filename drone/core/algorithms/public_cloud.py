import numpy as np
import logging
from drone.core.models import DroneGaussianProcess, select_ucb_action

logger = logging.getLogger(__name__)

class PublicCloudBandit:
    def __init__(self, action_space, alpha=0.5, beta=0.5, sliding_window_size=30, gp_hyperparams=None):
        self.action_space = action_space
        self.alpha = alpha
        self.beta = beta
        self.t = 1
        gp_params = gp_hyperparams or {}
        self.gp_model = DroneGaussianProcess(sliding_window_size=sliding_window_size, **gp_params)
        self.history = {'actions': [], 'contexts': [], 'rewards': [], 'performance': [], 'costs': []}

    def reward_function(self, performance, cost):
        return self.alpha * performance - self.beta * cost

    def select_action(self, context):
        d = self.action_space.shape[1] + context.shape[0]
        action, _ = select_ucb_action(action_space=self.action_space, context=context, 
                                      gp_model=self.gp_model, t=self.t, d=d)
        return action

    def update(self, action, context, performance, cost):
        reward = self.reward_function(performance, cost)
        X = np.array([np.concatenate([action, context])])
        y = np.array([reward])
        self.gp_model.update(X, y)
        self.history['actions'].append(action)
        self.history['contexts'].append(context)
        self.history['rewards'].append(reward)
        self.history['performance'].append(performance)
        self.history['costs'].append(cost)
        self.t += 1
        return reward

    def get_regret(self):
        if not self.history['rewards']:
            return 0.0
        best_reward = max(self.history['rewards'])
        return sum(best_reward - reward for reward in self.history['rewards'])

    def reset(self):
        self.gp_model.reset()
        self.t = 1
        self.history = {'actions': [], 'contexts': [], 'rewards': [], 'performance': [], 'costs': []}
