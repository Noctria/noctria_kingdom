# tests/test_dqn_agent.py
import numpy as np
from strategies.reinforcement.dqn_agent import DQNAgent

def test_decide_action_shape():
    agent = DQNAgent(state_dim=4, action_dim=2)
    state = np.array([0.1, 0.2, 0.3, 0.4])
    action = agent.decide_action(state, epsilon=0.0)
    assert action in [0, 1]

def test_update_runs_without_error():
    agent = DQNAgent(state_dim=4, action_dim=2)
    batch = (
        np.random.rand(5, 4),   # states
        np.random.randint(0, 2, size=5),  # actions
        np.random.rand(5),      # rewards
        np.random.rand(5, 4),   # next_states
        np.random.choice([True, False], size=5)  # dones
    )
    agent.update(batch)
