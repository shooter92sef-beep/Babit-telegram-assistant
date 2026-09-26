
# Bybit Telegram Assistant — read-only starter

Функции:
- Баланс Bybit Unified
- Открытые позиции
- Доступ только по вашему Telegram User ID
- Bybit API можно и нужно создать Read-Only

## Переменные окружения
TELEGRAM_BOT_TOKEN
TELEGRAM_USER_ID
BYBIT_API_KEY
BYBIT_API_SECRET

## Развёртывание на Render
1. Загрузите эти файлы в GitHub-репозиторий.
2. На Render создайте Web Service из репозитория.
3. Выберите Free.
4. Добавьте четыре переменные окружения.
5. После Deploy откройте:
   https://ВАШ-СЕРВИС.onrender.com/set-webhook
6. В Telegram отправьте боту /start.

ВАЖНО:
- Не публикуйте токены/API secret в GitHub.
- Для первой версии Bybit API key должен быть Read-Only.
- Не включайте Withdraw.
