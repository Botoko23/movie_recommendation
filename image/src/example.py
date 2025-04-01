import json

def lambda_handler(event: dict, context):
            # Process event data
    response = {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Lambda executed successfully!",
                "input": event
            })
        }
    
    return response
