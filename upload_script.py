import requests

url = "http://localhost:5000/upload"
file_path = "sample.txt"

with open(file_path, 'rb') as f:
    files = {'file': f}
    response = requests.post(url, files=files)

print(response.json())