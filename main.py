import os
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote

from bs4 import BeautifulSoup
from pathvalidate import sanitize_filepath, sanitize_filename
import requests


def check_for_redirect(response: requests.Response):
    for happend_response in response.history:
        if happend_response.status_code>=300:
            raise requests.HTTPError


def download_image(url, filename):
    """!!! filename must be a valid path to the image file !!!"""
    response = requests.get(url)
    response.raise_for_status()
    if not os.path.exists(filename):
        with open(filename, 'wb') as file:
            file.write(response.content)


def download_book(url, filename):
    response = requests.get(url)
    check_for_redirect(response)
    response.raise_for_status()
    with open(filename, 'wt') as file:
        file.write(response.text)


def download_books():
    Path('books').mkdir(parents=True, exist_ok=True)
    for i in range(2,3):
        try:
            download_book(f'https://tululu.org/txt.php?id={i}',
                       f'books/book-{i}.txt')
        except requests.HTTPError:
           pass


def download_txt(url, filename, folder='books/'):
    """Функция для скачивания текстовых файлов.
    Args:
        url (str): Cсылка на текст, который хочется скачать.
        filename (str): Имя файла, с которым сохранять.
        folder (str): Папка, куда сохранять.
    Returns:
        str: Путь до файла, куда сохранён текст.
    """
    san_folder = sanitize_filepath(folder)
    Path(san_folder).mkdir(parents=True, exist_ok=True)
    filepath=os.path.join(folder, sanitize_filename(f'{filename}.txt'))
    download_book(url=url, filename=filepath)
    return filepath


def download_books_with_title():
    Path('images').mkdir(parents=True, exist_ok=True)
    for i in range(1,11):
        response = requests.get(f'https://tululu.org/b{i}/')
        response.raise_for_status()
        try:
            check_for_redirect(response)
        except requests.HTTPError:
            pass
        else:
            soup = BeautifulSoup(response.text, 'lxml')
            splitted_text = soup.find('h1').text.split('::')
            book_file = f'{i}. {splitted_text[0].strip()}'
            # img_path = soup.find('div', class_='bookimage').find('img')['src']
            # img_url = urljoin(response.url, img_path)
            # img_file_name = os.path.basename(unquote(img_path))
            # comments_tags = soup.find_all('div', class_='texts')
            genre_tags = soup.find('span', class_='d_book')
            genres = [a.text for a in genre_tags.find_all('a')]
            print(book_file, '\n', genres)
            # for comment in comments_tags:
            #     print(comment.span.text)
            # download_image(img_url, os.path.join('images', img_file_name))
            # try:
            #     download_txt(f'https://tululu.org/txt.php?id={i}',book_file)
            # except requests.HTTPError:
            #     pass


    # image_tag = soup.find('img', class_='attachment-post-image')['src']
    # print(image_tag, '\n')
    # entry_html = soup.find('div', class_='entry-content')
    # print(entry_html.text)


if __name__ == "__main__":
    download_books_with_title()

