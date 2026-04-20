import json, boto3, torch, time
from transformers import AutoTokenizer, T5ForConditionalGeneration
from decimal import Decimal

MODEL_PATH = "/var/task/t5_empathetic_4class"
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)
model = T5ForConditionalGeneration.from_pretrained(MODEL_PATH, local_files_only=True)
model.eval()

ddb = boto3.resource("dynamodb")
table = ddb.Table("mental-health-conversations")

def lambda_handler(event, context):
    raw_body = event.get("body", {})
    if isinstance(raw_body, str):
        body = json.loads(raw_body)
    elif isinstance(raw_body, dict):
        body = raw_body
    else:
        body = event
    user_input = body.get("safe_input", "")
    emotion = body.get("emotion", "neutral")
    session_id = body.get("session_id", "anon")

    # Generate response
    prompt = f"emotion: {emotion} message: {user_input}"
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=150,
            num_beams=4,
            no_repeat_ngram_size=3,
            early_stopping=True
        )

    response = tokenizer.decode(output_ids[0], skip_special_tokens=True)

    # Save to DynamoDB
    table.put_item(Item={
        "session_id": session_id,
        "timestamp": Decimal(str(time.time())),
        "user_input": user_input,
        "emotion": emotion,
        "response": response
    })

    return {
        "statusCode": 200,
        "body": json.dumps({
            "response": response,
            "emotion": emotion
        })
    }