import torch
import torch.nn as nn
import copy

class TargetNetwork:
    def __init__(self, model, update_interval=1000):
        """ DQN のターゲットネットワークを管理 """
        self.model = model
        self.target_model = copy.deepcopy(model)
        self.update_interval = update_interval
        self.step_count = 0

    def update_target(self):
        """ 一定ステップごとにターゲットネットワークを更新 """
        self.target_model.load_state_dict(self.model.state_dict())

    def select_action(self, state):
        """ ターゲットネットワークを利用して最適行動を選択 """
        with torch.no_grad():
            state_tensor = torch.tensor(state, dtype=torch.float32)
            q_values = self.target_model(state_tensor)
        return torch.argmax(q_values).item()

    def increment_step(self):
        """ ステップをカウントし、必要ならターゲットを更新 """
        self.step_count += 1
        if self.step_count % self.update_interval == 0:
            self.update_target()
