import io
import os
import time
from datetime import datetime
from io import BytesIO

from PIL import Image
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Читаем ключи АПИ из файла .env
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
BASE_URL = os.getenv("BASE_URL")
API_VERSION = os.getenv("API_VERSION")

# Инициализация ИИ клиента
options = http_options = types.HttpOptions(base_url=BASE_URL, api_version=API_VERSION)
client = genai.Client(api_key=GOOGLE_API_KEY, http_options=options)

# Модели — для работы с картинками и видео
IMAGE_MODEL = "gemini-2.5-flash-image"
VIDEO_MODEL = "veo-3.0-fast-generate-001"

# Настройки безопасности
safety_settings = [
    # Разрешаем «хоррор» и кровь как художественный/киношный образ
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    # Любой сексуальный контент блокируем максимально строго.
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
]


# Создание картинки на основе текстового описания
def ai_create_image(prompt: str, output_path):
    config = types.GenerateContentConfig(safety_settings=safety_settings)
    response = client.models.generate_content(model=IMAGE_MODEL, contents=[prompt], config=config)
    _save_image_if_exist(response, output_path)


# Редактирование картинки с помощью текстовых инструкций
def ai_edit_image(input_image_path: str, prompt: str, output_path):
    image = Image.open(input_image_path)

    config = types.GenerateContentConfig(safety_settings=safety_settings)
    response = client.models.generate_content(model=IMAGE_MODEL, contents=[image, prompt], config=config)
    _save_image_if_exist(response, output_path)


# Объединение нескольких картинок с помощью текстовых инструкций
def ai_merge_image(input_image_path_list: list, prompt: str, output_path):
    data = [Image.open(image_path) for image_path in input_image_path_list]
    data.append(prompt)

    config = types.GenerateContentConfig(safety_settings=safety_settings)
    response = client.models.generate_content(model=IMAGE_MODEL, contents=data, config=config)
    _save_image_if_exist(response, output_path)


# Создание видео на основе текстового описания
def ai_video_from_text(prompt: str, out_path):
    config = types.GenerateVideosConfig(aspect_ratio="16:9", number_of_videos=1)
    op = client.models.generate_videos(model=VIDEO_MODEL, prompt=prompt, config=config)
    _save_video_if_exist(op, out_path)


# Создание видео из картинки и текстового описания
def ai_video_from_text_and_image(prompt: str, input_image_path: str, out_path):
    # Загружаем картинку в буфер перед отправкой
    im = Image.open(input_image_path)

    image_bytes_io = io.BytesIO()
    im.save(image_bytes_io, format=im.format)
    image_bytes = image_bytes_io.getvalue()

    image = types.Image(image_bytes=image_bytes, mime_type=im.format)

    config = types.GenerateVideosConfig(aspect_ratio="9:16", number_of_videos=1, )
    op = client.models.generate_videos(model=VIDEO_MODEL, prompt=prompt, image=image, config=config)

    _save_video_if_exist(op, out_path)


# Обрабатывает ответ сервера
def _save_image_if_exist(response, output_path: str):
    # Пустой ответ
    if not response.candidates:
        raise RuntimeError("ИИ не смог создать картинку. Попробуйте другой промпт.")

    cand = response.candidates[0]

    # Проверяем, не сработал ли фильтр
    if cand.finish_reason and cand.finish_reason.name == "IMAGE_SAFETY":
        raise RuntimeError("Запрос отклонён фильтрами безопасности. Попробуйте изменить описание.")

    if not cand.content or not cand.content.parts:
        raise RuntimeError("Ответ от ИИ не содержит изображения.")

    # обычная обработка
    for part in cand.content.parts:
        if part.text is not None:
            print(part.text)
        elif part.inline_data is not None:
            image = Image.open(BytesIO(part.inline_data.data))

            image = image.convert("RGB")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            rename_with_timestamp(output_path)
            image.save(output_path, format="JPEG", quality=95)
            return True

    raise RuntimeError("Ответ от ИИ не содержит изображения.")


# Ждёт завершения операции генерации видео и сохраняет результат.
def _save_video_if_exist(op: types.GenerateVideosOperation, output_path: str, timeout: int = 300) -> bool:
    start = time.time()

    # Ждём завершения
    while not op.done:
        if time.time() - start > timeout:
            raise TimeoutError("Ожидание генерации видео превысило 5 минут.")
        time.sleep(3)
        op = client.operations.get(op)

    # Проверяем, есть ли ответ
    if not getattr(op, "response", None):
        raise RuntimeError("Видео не сгенерировано: пустой ответ от модели.")

    if not getattr(op.response, "generated_videos", None):
        raise RuntimeError("Видео не сгенерировано: список пуст.")

    vid = op.response.generated_videos[0]

    # Проверка finish_reason (например, SAFETY)
    if hasattr(vid, "finish_reason") and vid.finish_reason:
        if vid.finish_reason.name.endswith("SAFETY"):
            raise RuntimeError(f"Видео отклонено фильтрами безопасности: {vid.finish_reason.name}")

    # Скачиваем и сохраняем
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    client.files.download(file=vid.video)
    rename_with_timestamp(output_path)
    vid.video.save(output_path)
    return True


# Создаем директорию для файлов пользователя
def create_user_dir(user_id):
    os.makedirs(f"resources/users/{user_id}", exist_ok=True)


# Сохраняем старые фото и видео (для отладки)
def rename_with_timestamp(file_path: str):
    if not os.path.isfile(file_path):
        return

    # Получаем директорию, имя и расширение
    directory, filename = os.path.split(file_path)
    name, ext = os.path.splitext(filename)

    # Формируем новый штамп времени
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Новое имя файла
    new_filename = f"{name}_{timestamp}{ext}"
    new_path = os.path.join(directory, new_filename)

    # Переименовываем
    os.rename(file_path, new_path)
