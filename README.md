Парсер государственных тендеров.

1.Обход первых двух страниц (44-ФЗ).

2.Сбор ссылок на печатные формы тендеров.

3.Замена view.html → viewXml.html и парсинг XML.

4.Извлечение поля publishDTInEIS (или None, если его нет).

5.Вывод результата прямо в консоль.

6.Распараллеливание (разбивка на Celery-таски)

7.Сбор ссылок со страниц — отдельная задача.

8.Парсинг XML — отдельная задача.

9.Использование eager-режима для упрощённого тестирования (всё выполняется синхронно).


