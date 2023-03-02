import sys
import os
import argparse
import json
from urllib.parse import urljoin
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from pathvalidate import sanitize_filepath, sanitize_filename

from tululu import (parse_book_page, get_response, check_for_redirect,
                    download_book, download_image)


def get_books_urls(page_start, page_end=None):
    page_base_url = 'https://tululu.org/l55/'
    book_urls = []
    response = get_response(page_base_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'lxml')
    max_page = int(soup.select('a.npage')[-1].text)
    if page_start > max_page:
        print(f'Первая страница, указанная при вызове скрипта больше'
              f' максимального числа страниц ({max_page})')
        sys.exit()
    if page_end:
        if page_end > max_page:
            print(f'Последняя страница, указанная при вызове скрипта, превышает '
                  f'максимальное число страниц ({max_page})\n'
                  f'будут скачаны книги со страниц {page_start}-{max_page}')
            page_end_checked = max_page + 1
        else:
            page_end_checked = page_end + 1
    else:
        print(f'Будут скачаны книги со страниц {page_start}-{max_page}')
        page_end_checked = max_page + 1
    for page in range(page_start, page_end_checked):
        url = urljoin(page_base_url, str(page))
        response = get_response(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        selector = 'div#content table.d_book'
        tables = soup.select(selector)
        for table in tables:
            href = table.tr.a['href']
            book_urls.append({
                'url': urljoin('https://tululu.org/', href),
                'id': href.removeprefix('/b').removesuffix('/')
            })
    return book_urls


def main():
    parser = argparse.ArgumentParser(description="Load txt books from tululu.org from pages")
    parser.add_argument("--first_page", type=int, help="Первая страница", default=1)
    parser.add_argument("--last_page", type=int, help="Последняя страница")
    parser.add_argument("-df", "--dest_folder", type=str, default='books', help="папка, в которую будут скачаны книги"
                                                                                ", изображения обложек и помещен "
                                                                                "json-файл с информацией о книгах.")
    parser.add_argument('--skip_imgs', action='store_true', help='Не скачивать изображения обложек')
    parser.add_argument('--skip_txt', action='store_true', help='Не скачивать книги')
    parser.add_argument('--json_path',type=str , help='указать свой путь к *.json файлу с информацией'
                                            ' о книгах')

    args = parser.parse_args()
    first_page = args.first_page
    last_page = args.last_page
    folder = args.dest_folder
    skip_imgs = args.skip_imgs
    skip_txt = args.skip_txt
    json_path = args.json_path
    if last_page and last_page < first_page:
        print('Последня страница не может быть меньше первой')
        return
    if first_page <= 0:
        print('Первая страница должна быть не менее 1')
        return
    book_urls = get_books_urls(first_page, last_page)
    san_folder = sanitize_filepath(folder)
    Path(san_folder, 'images').mkdir(parents=True, exist_ok=True)
    if json_path:
        san_json_path = sanitize_filepath(json_path)
        json_folder = os.path.split(json_path)[0]
        Path(json_folder).mkdir(parents=True, exist_ok=True)
    else:
        san_json_path = Path(san_folder, 'book_info.json')
    books_info = []
    count = 0
    print('Ссылки на страницы книг получены.',
          '\nТекст книг скачан не будет (задана опция --skip_txt)' if skip_txt else '',
          '\nИзображения обложек скачаны не будут (задана опция --skip_imgs)' if skip_imgs else '',
          '\nНачинаем обработку ссылок...\n')
    for num, book_url in enumerate(book_urls):
        print(f'Обработка {book_url["url"]}')
        url = book_url['url']
        book_id = book_url['id']
        try:
            response = get_response(book_url['url'])
            response.raise_for_status()
            check_for_redirect(response)
        except requests.HTTPError as e:
            print(f'Не удается найти главную страницу книги по адресу: {url}'
                  , file=sys.stderr)
        except requests.ConnectionError as e:
            print('Проблема с интернет-соединением', file=sys.stderr)
            print(e)
            sys.exit()
        else:
            book_parsed = parse_book_page(response.text, response.url)
            if not skip_txt:
                try:
                    params = {'id': book_id}
                    count += 1
                    if count == 3:
                        break
                    filepath = os.path.join(san_folder, sanitize_filename(f'{count}-я книга. {book_parsed["title"]}.txt'))
                    response = download_book('https://tululu.org/txt.php', params, filepath)
                    book_parsed['book_path'] = filepath
                except requests.HTTPError:
                    print(f'Не удается найти ссылку для загрузки книги: {response.url}', file=sys.stderr)
                    book_parsed['book_path'] = 'Не удалось найти ссылку для загрузки книги'
                    count -= 1
                except requests.ConnectionError as e:
                    print('Проблема с интернет-соединением', file=sys.stderr)
                    print(e)
                    sys.exit()
            if not skip_imgs:
                try:
                    img_path = Path(Path.cwd(), san_folder,
                                    'images', book_parsed['img_file_name'])
                    download_image(book_parsed['img_url'], img_path)
                except requests.HTTPError:
                    print(f'Не удается скачать изображение с URL: {book_parsed["img_url"]}', file=sys.stderr)
                except requests.ConnectionError as e:
                    print('Проблема с интернет-соединением', file=sys.stderr)
                    print(e)
                    sys.exit()
            books_info.append(book_parsed)
    if not skip_txt:
        print(f'\nВсего скчано книг: {count}')
    books_json = json.dumps(books_info, ensure_ascii=False, indent=4)
    with open(san_json_path, "w") as my_file:
        my_file.write(books_json)


if __name__ == "__main__":
   main()