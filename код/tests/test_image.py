import requests

IP = "192.168.0.110"

try:

    print("GET request")

    response = requests.get(
        f"http://{IP}/image",
        timeout=10
    )

    print("Status:", response.status_code)

    data = response.content

    print("Bytes:", len(data))

    with open("test.jpg", "wb") as file:
        file.write(data)

    print("Файл сохранён")

except Exception as e:

    print("Ошибка:")
    print(type(e).__name__)
    print(e)