import requests

url = "http://localhost:8000/api/generate_script_sse"
response = requests.post(url, json={"source_text": "这是一个测试博文"}, stream=True)
for line in response.iter_lines():
    if line:
        print(line.decode('utf-8'))
