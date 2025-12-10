import requests
import json

data = {'user': {
            'username': 'P',
            'email': 'ksf@k.ru',
            'password': '1'
        }
}
print(data)
response = requests.post('http://127.0.0.1:8000/api/users/login/', json=data)
print(response)
print(response.text)