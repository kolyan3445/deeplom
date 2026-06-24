import requests

IP = "192.168.0.110"

try:

    print("Начало")

    response = requests.get(
        f"http://{IP}/image",
        timeout=10,
        stream=True
    )

    print("Статус:", response.status_code)

    total = 0

    for chunk in response.iter_content(1024):

        if chunk:

            total += len(chunk)

            print(
                f"Получено: {total} байт"
            )

    print("Готово")

except Exception as e:

    print("Ошибка:")
    print(type(e).__name__)
    print(e)