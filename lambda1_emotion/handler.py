import json, boto3, os, torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

MODEL_PATH = "/var/task/distilbert_4class"
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH, local_files_only=True)
model.eval()

# Your actual labels from config
LABELS = {0: "sadness", 1: "joy", 2: "anger", 3: "fear"}

# Crisis keywords — triggers safe response regardless of DistilBERT
CRISIS_KEYWORDS = [
    "hurt myself", "kill myself", "suicide", "suicidal",
    "don't want to live", "dont want to live", "end my life",
    "want to die", "self harm", "self-harm", "no reason to live"
]

SAFE_RESPONSES = {
    "crisis":  "I am concerned about you. I am an AI and cannot provide crisis intervention. Please reach out to a professional immediately: [(02) 713 6793 (Thai), (02) 713-6791 (English)].",
    "sadness": "I'm sorry you're feeling this way. Would you like to talk more about what's going on?",
    "fear":    "That sounds really overwhelming. What's been worrying you the most?",
    "anger":   "It sounds like you're going through something really frustrating. Do you want to talk about it?",
    "joy":     "That's wonderful to hear! Tell me more."
}

lambda_client = boto3.client("lambda")

def lambda_handler(event, context):
    body = json.loads(event.get("body", "{}"))
    user_input = body.get("message", "").strip()
    session_id = body.get("session_id", "anon")

    # Input validation
    if not user_input or len(user_input) > 2000:
        return {"statusCode": 400, "body": json.dumps({"error": "Invalid input"})}

    # Crisis keyword check FIRST before anything else
    user_lower = user_input.lower()
    if any(kw in user_lower for kw in CRISIS_KEYWORDS):
        return {
            "statusCode": 200,
            "body": json.dumps({
                "response": SAFE_RESPONSES["crisis"],
                "emotion": "crisis",
                "routed_to": "safe_response"
            })
        }

    # Emotion detection with DistilBERT
    inputs = tokenizer(user_input, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        logits = model(**inputs).logits
    emotion = LABELS[logits.argmax().item()]

    # Invoke Lambda 2 for response generation
    resp = lambda_client.invoke(
        FunctionName=os.environ["LAMBDA2_ARN"],
        InvocationType="RequestResponse",
        Payload=json.dumps({
            "body": json.dumps({
                "safe_input": user_input,
                "emotion": emotion,
                "session_id": session_id
            })
        })
    )
    result = json.loads(resp["Payload"].read())
    return result