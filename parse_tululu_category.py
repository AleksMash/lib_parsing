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


def get_books_urls(page_start, page_end):
    page_base_url = 'https://tululu.org/l55/'
    book_urls = []
    for page in range(page_start, page_end+1):
        url = urljoin(page_base_url, str(page))
        response = get_response(url)
        soup = BeautifulSoup(response.text, 'lxml')
        div = soup.find('div', id='content')
        tables = div.find_all('table', class_='d_book')
        for table in tables:
            href: str = table.tr.a['href']
            book_urls.append({
                'url': urljoin('https://tululu.org/', href),
                'id': href.removeprefix('/b').removesuffix('/')
            })
    return book_urls


def main():
    parser = argparse.ArgumentParser(description="Load txt books from tululu.org from pages")
    parser.add_argument("first_page", type=int, help="Первая страница")
    parser.add_argument("last_page", type=int, help="Последняя страница")
    parser.add_argument("-f", "--folder", type=str, default='books', help="папка, в которую будут скачаны книги")
    args = parser.parse_args()
    first_page = args.first_page
    last_page = args.last_page
    print(f'Грузим страницы {first_page} по {last_page}')
    folder = args.folder
    if last_page < first_page:
        print('Последня страница не может быть меньше первой')
        return
    if first_page <= 0:
        print('Первая страница должна быть не менее 1')
        return
    book_urls = get_books_urls(first_page, last_page+1)
    Path('images').mkdir(parents=True, exist_ok=True)
    san_folder = sanitize_filepath(folder)
    Path(san_folder).mkdir(parents=True, exist_ok=True)
    books_info = []
    count = 0
    for num, book_url in enumerate(book_urls):
        if count == 3:
            break
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
            try:
                params = {'id': book_id}
                count += 1
                print(f'Грузим книгу {count}', url)
                filepath = os.path.join(san_folder, sanitize_filename(f'{count}-я книга. {book_parsed["title"]}.txt'))
                response = download_book('https://tululu.org/txt.php', params, filepath)
            except requests.HTTPError as e:
                print(f'Не удается скачать книгу с URL: {response.url}', file=sys.stderr)
                count -= 1
            except requests.ConnectionError as e:
                print('Проблема с интернет-соединением', file=sys.stderr)
                print(e)
                sys.exit()
            else:
                try:
                    download_image(book_parsed['img_url'], os.path.join('images', book_parsed['img_file_name']))
                except requests.HTTPError as e:
                    print(f'Не удается скачать изображение с URL: {book_parsed["img_url"]}', file=sys.stderr)
                except requests.ConnectionError as e:
                    print('Проблема с интернет-соединением', file=sys.stderr)
                    print(e)
                    sys.exit()
                book_parsed['book_path'] = filepath
                book_parsed.pop('img_file_name')
                books_info.append(book_parsed)
        books_json = json.dumps(books_info, ensure_ascii=False, indent=4)
        info_file_path = os.path.join(san_folder, 'books_info.json')
        with open(info_file_path, "w", ) as my_file:
            my_file.write(books_json)


if __name__ == "__main__":
    main()