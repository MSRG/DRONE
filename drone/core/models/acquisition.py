import numpy as np

def ucb(X, gp_model, beta=2.0):
    mean, std = gp_model.predict(X)
    ucb_values = mean + np.sqrt(beta) * std
    return ucb_values

def ucb_beta(t, d, B=1.0):
    gamma_t = d * np.log(t + 1)
    log_term = np.log(max(t / B, 1.0))
    zeta_t = 2 * (B ** 2) + 300 * gamma_t * (log_term ** 3)
    return zeta_t

def select_ucb_action(action_space, context, gp_model, t, d=None, safe_set=None):
    if d is None:
        d = action_space.shape[1] + context.shape[0]
    beta_t = ucb_beta(t, d)
    if safe_set is None:
        safe_set = action_space
    inputs = np.array([np.concatenate([action, context]) for action in safe_set])
    ucb_values = ucb(inputs, gp_model, beta=beta_t)
    best_idx = np.argmax(ucb_values)
    best_action = safe_set[best_idx]
    best_ucb = ucb_values[best_idx]
    return best_action, best_ucb
