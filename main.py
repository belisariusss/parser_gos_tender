import requests
from bs4 import BeautifulSoup
import xmltodict
import time
from celery import Celery

app = Celery("tenders")


app.conf.update(
    task_always_eager=True,
    result_backend="rpc://",  
    broker_url="memory://",  
)



def fetch_with_retries(url, headers=None, max_retries=3, delay=2):
    """
    Делает GET-запрос по URL с несколькими повторными попытками.
    :param url: URL для запроса
    :param headers: Заголовки запроса
    :param max_retries: Максимальное число попыток
    :param delay: Задержка (в секундах) между попытками
    :return: response или None, если так и не удалось получить ответ со статусом 200
    """
    if headers is None:
        headers = {}
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                return resp  
            else:
                print(f"Ошибка {resp.status_code} при запросе {url}, попытка {attempt+1}")
        except requests.exceptions.RequestException as e:
            print(f"Сетевая ошибка: {e}, попытка {attempt+1}")

        if attempt < max_retries - 1:
            time.sleep(delay)
    return None




@app.task
def get_tender_links_task(page_number):
    """
    Задача (таск) для сбора ссылок на печатные формы со страницы page_number.
    """
    url = f"https://zakupki.gov.ru/epz/order/extendedsearch/results.html?fz44=on&pageNumber={page_number}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    response = fetch_with_retries(url, headers=headers, max_retries=3, delay=2)
    if not response:
        print(f"Ошибка при получении страницы {page_number} после нескольких попыток")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    tenders = soup.find_all("div", class_="registry-entry__header-mid__number")
    
    links = []
    for tender in tenders:
        a_tag = tender.find("a")
        if a_tag:
            tender_number = a_tag.text.strip().replace("№", "").strip()
            link = f"https://zakupki.gov.ru/epz/order/notice/printForm/view.html?regNumber={tender_number}"
            links.append(link)
    
    return links


@app.task
def parse_tender_xml_task(print_form_url):
    """
    Задача (таск) для парсинга XML-формы по ссылке на HTML-форму.
    Возвращает кортеж (print_form_url, publishDTInEIS).
    """
    xml_url = print_form_url.replace('view.html', 'viewXml.html')
    headers = {"User-Agent": "Mozilla/5.0"}
    
    response = fetch_with_retries(xml_url, headers=headers, max_retries=3, delay=2)
    if not response:
        print(f"Ошибка загрузки XML по ссылке: {xml_url} после нескольких попыток")
        return print_form_url, None

    try:
        data_dict = xmltodict.parse(response.text)
    except Exception as e:
        print(f"Ошибка парсинга XML: {e}")
        return print_form_url, None

    def find_publish_dt_in_eis(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == 'publishDTInEIS':
                    return v
                result = find_publish_dt_in_eis(v)
                if result is not None:
                    return result
        elif isinstance(obj, list):
            for item in obj:
                result = find_publish_dt_in_eis(item)
                if result is not None:
                    return result
        return None

    publish_dt_in_eis = find_publish_dt_in_eis(data_dict)
    return print_form_url, publish_dt_in_eis




def main():
    all_links = []
    for page in range(1, 3):
        task_result = get_tender_links_task.delay(page)
        links = task_result.get()
        
        print(f"Страница {page}:")
        for link in links:
            print(link)
        all_links.extend(links)
    
    for link in all_links:
        parse_task_result = parse_tender_xml_task.delay(link)
        print_form_url, publish_dt = parse_task_result.get()
        print(f"{print_form_url} - {publish_dt}")

if __name__ == "__main__":
    main()
