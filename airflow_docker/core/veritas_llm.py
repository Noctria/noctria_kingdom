from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

MODEL_DIR = "/noctria_kingdom/airflow_docker/models/nous-hermes-2"

model = AutoModelForCausalLM.from_pretrained(MODEL_DIR)
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)

def generate_fx_strategy(prompt: str) -> str:
    inputs = tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        outputs = model.generate(inputs["input_ids"], max_new_tokens=300)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)
