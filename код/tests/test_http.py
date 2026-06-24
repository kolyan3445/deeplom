import requests

IP = "192.168.0.110"  # замени на свой

try:
    print("Отправка запроса...")

    response = requests.get(
        f"http://{IP}/image",
        timeout=10
    )

    print("Статус:", response.status_code)
    print("Заголовки:")

    for key, value in response.headers.items():
        print(f"{key}: {value}")

except Exception as e:
    print("Ошибка:")
    print(type(e).__name__)
    print(e)