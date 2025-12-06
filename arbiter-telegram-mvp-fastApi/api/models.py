from transformers import pipeline
import torch


def get_device():
    if torch.cuda.is_available():
        return 0  # Use CUDA (GPU)
    elif torch.backends.mps.is_available():
        return "mps"  # Use Apple Silicon GPU
    else:
        return -1  # Use CPU


class SentimentAnalyser:
    model_name = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
    device = get_device()
    pipeline = pipeline('sentiment-analysis', model=model_name, tokenizer=model_name, device=device)

    @staticmethod
    def predict(text: list | str):
        results = SentimentAnalyser.pipeline(text)
        return results


class EmotionAnalyser:
    model_name = "bhadresh-savani/distilbert-base-uncased-emotion"
    device = get_device()
    pipeline = pipeline('text-classification', model=model_name, tokenizer=model_name, device=device)

    @staticmethod
    def predict(text: list | str):
        results = EmotionAnalyser.pipeline(text)
        return results


class ToxicityAnalyser:
    model_name = "unitary/toxic-bert"
    device = get_device()
    pipeline = pipeline("text-classification", model=model_name, device=device, top_k=5)

    @staticmethod
    def predict(text: list | str):
        result = ToxicityAnalyser.pipeline(text)
        return result
