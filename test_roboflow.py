import os

from inference_sdk import (
    InferenceHTTPClient,
    InferenceConfiguration
)

client = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key=os.environ["ROBOFLOW_API_KEY"]
).configure(
    InferenceConfiguration(
        api_key_transport="header"
    )
)

result = client.run_workflow(
    workspace_name="sahil-singh-nepyt",
    workflow_id="vehicle-number-plate-ocr-1787901794956",
    images={
        "image": "test.jpeg"
    },
    use_cache=True
)

plate_text = result[0].get("plate_text", [])

if plate_text:
    print("Detected plate:", plate_text[0])
else:
    print("No plate detected")