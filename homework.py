import logging
import os
import time

import requests
import telegram
from requests.exceptions import RequestException
from dotenv import load_dotenv

from exception import (EndpointError,
                       SendMessageException)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

CONNECTION_ERROR = '{error}, {url}, {headers}, {params}'
WRONG_ENDPOINT = '{response_status}, {url}, {headers}, {params}'
FORMAT_NOT_JSON = 'Формат не json {error}'

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG)

logger = logging.getLogger(__name__)


def check_tokens():
    """Проверка доступности переменных окружения."""
    if PRACTICUM_TOKEN is None:
        logger.critical('Переменная PRACTICUM_TOKEN не корректна')
        return False
    if TELEGRAM_TOKEN is None:
        logger.critical('Переменная TELEGRAM_TOKEN не корректна')
        return False
    if TELEGRAM_CHAT_ID is None:
        logger.critical('Переменная TELEGRAM_CHAT_ID не корректна')
        return False
    return True


def send_message(bot, message):
    """Отправка сообщения в Telegram."""
    bot.send_message(chat_id=TELEGRAM_CHAT_ID,
                     text=message)
    logger.debug(f'Бот отправил сообщение: {message}')


def get_api_answer(timestamp):
    """Запрос к эндпоинту API-сервиса."""
    time_params = {'from_date': timestamp}
    all_params = dict(url=ENDPOINT,
                      headers=HEADERS,
                      params=time_params)
    try:
        response = requests.get(**all_params)
    except RequestException as error:
        raise telegram.TelegramError(CONNECTION_ERROR.format(
            error=error,
            **all_params,
        ))
    if response.status_code != 200:
        raise EndpointError(WRONG_ENDPOINT.format(
            response_status=response.status_code,
            **all_params,
        ))
    return response.json()


def check_response(response):
    """Проверка ответа API от эндпоинта."""
    if not isinstance(response,
                      dict):
        error = 'Неверный тип данных одноразовых переменных'
        raise TypeError(error)
    elif 'homeworks' not in response:
        error = 'В ответе от API отсутствует ключ homeworks'
        raise KeyError(error)
    elif not isinstance(response['homeworks'],
                        list):
        error = 'Неверный тип данных у элемента homeworks'
        raise TypeError(error)


def parse_status(homework):
    """Извлечение статуса конкретной домашней работы."""
    try:
        homework_name = homework['homework_name']
    except KeyError:
        logger.error('В ответе от API отсутствует ключ homeworks_name')
        raise Exception('В ответе от API отсутствует ключ homeworks_name')
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        raise KeyError('Статус домашней работы не распознан')
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise Exception('Ошибка глобальных переменных. Смотрите логи')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    logging.info('Запущен бот по проверке задания')
    timestamp = int(time.time())
    last_status = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homework = response.get('homeworks')
            if homework:
                status = parse_status(homework[0])
                if status != last_status:
                    send_message(bot, status)
                    last_status = status
            else:
                message = 'Статус работы не изменился'
                logger.debug(message)
        except telegram.TelegramError as error:
            message = f'Не удалось отправить сообщение - {error}'
            logger.error(message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logger.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
