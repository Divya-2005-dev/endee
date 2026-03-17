import requests

url = "http://localhost:5000/ask"
question = "What is the project about?"

response = requests.post(url, json={"question": question})

print(response.json())