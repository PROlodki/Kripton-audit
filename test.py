import requests
import json

data = {'user': {
            'username': 'Prolodkis',
            'email': 'ovchinnickov.vasilij2016@yandex.ru',
            'password': 'Permm2010'
        }
}
data = json.dumps(data)
print(data)
response = requests.post('http://127.0.0.1:8000/api/users/login/', data)
print(response)