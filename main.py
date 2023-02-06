import os
import argparse
from pathlib import Path
from urllib.parse import urljoin, unquote

from bs4 import BeautifulSoup
from pathvalidate import sanitize_filepath, sanitize_filename
import requests


def check_for_redirect(response: requests.Response):
    for happend_response in response.history:
        if happend_response.status_code>=300:
            raise requests.HTTPError


def parse_book_page(html, page_url):
    '''Return dict with parsed book data:
        title, author, genres (list), comments (list), image file name, title image URL
    Arguments:
        html - html (str) content of the web page.
        page_url - URL of the page'''
    soup = BeautifulSoup(html, 'lxml')
    splitted_text = soup.find('h1').text.split('::')
    book_title = splitted_text[0].strip()
    author = splitted_text[1].strip()
    img_path = soup.find('div', class_='bookimage').find('img')['src']
    img_url = urljoin(page_url, img_path)
    img_file_name = os.path.basename(unquote(img_path))
    comments_tags = soup.find_all('div', class_='texts')
    comments = [c.span.text for c in comments_tags]
    genre_tags = soup.find('span', class_='d_book')
    genres = [a.text for a in genre_tags.find_all('a')]
    return {
        'title':book_title,
        'author':author,
        'genres':genres,
        'comments':comments,
        'img_file_name':img_file_name,
        'img_url':img_url
    }


def download_image(url, filename):
    """!!! filename must be a valid path
     to the image file. Ensure that it is properly prepared!!!"""
    response = requests.get(url)
    response.raise_for_status()
    if not os.path.exists(filename):
        with open(filename, 'wb') as file:
            file.write(response.content)


def download_book(url, filename):
    """!!! filename must be a valid path
     to the *.txt file !!! Ensure that it is properly prepared"""
    response = requests.get(url)
    check_for_redirect(response)
    response.raise_for_status()
    with open(filename, 'wt') as file:
        file.write(response.text)


def download_books_with_title(first, last, folder):
    Path('images').mkdir(parents=True, exist_ok=True)
    san_folder = sanitize_filepath(folder)
    Path(san_folder).mkdir(parents=True, exist_ok=True)
    for i in range(first,last+1):
        response = requests.get(f'https://tululu.org/b{i}/')
        response.raise_for_status()
        try:
            check_for_redirect(response)
        except requests.HTTPError:
            pass
        else:
            book_data = parse_book_page(response.text, response.url)
            filepath = os.path.join(san_folder, sanitize_filename(f'{i}. {book_data["title"]}.txt'))
            try:
                download_book(f'https://tululu.org/txt.php?id={i}', filepath)
            except requests.HTTPError:
                pass
            download_image(book_data['img_url'], os.path.join('images', book_data['img_file_name']))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load txt books from tululu.org")
    parser.add_argument("first_id", type=int, help="ID первой книги")
    parser.add_argument("last_id", type=int, help="ID последней книги")
    parser.add_argument("-f", "--folder", type=str, default='books', help="папка, в которую будут скачаны книги")
    args = parser.parse_args()
    download_books_with_title(args.first_id, args.last_id, args.folder)
