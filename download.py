#!/usr/bin/env python3

# Download the video from file-up.org page
# Example: https://www.file-up.org/5ggryv3orudj

import os
import sys
import argparse
import requests
import logging
from tqdm import tqdm
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from fake_useragent import UserAgent


def humanize(size, suffix='B'):
    """ Return a human readable string for the given size """
    if size is None:
        return "Not Avbl"
    for unit in ['B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(size) < 1024.0:
            return '%3.1f %s%s' % (size, unit, suffix)
        size /= 1024.0
    return '%.1f %s%s' % (size, 'Yi', suffix)


def download_file_up(weblink):
    """ Download video from file-up.org """
    u = urlparse(weblink)
    code = u.path.strip('/')
    target = code + '.mp4'

    if os.path.exists(target):
        return '{} already exists. Skipping.'.format(target)

    embed_url = '{}://{}/embed-{}-1110x500.html'.format(
        u.scheme, u.netloc, code)
    logging.debug('Requesting %s', embed_url)
    response = requests.get(embed_url, headers=headers)
    if not response:
        return 'GET {} failed: {}'.format(embed_url, response.status_code)
    logging.debug('Retrieved %s', embed_url)

    soup = BeautifulSoup(response.text, features='html.parser')
    tag = soup.find('div', id='player_code')
    if not tag:
        return 'No player_code div in {}'.format(embed_url)
    start = tag.text.index(',36,')
    data = tag.text[start:].split(',')
    bits = data[3].split('.')[0]
    b = bits.split('|')
    scheme = secret = server = None
    for idx, item in enumerate(b):
        if item in ['https']:
            scheme = b[idx]
        elif len(item) > 40:
            secret = b[idx]
        elif len(item) < 4 and item.startswith('f'):
            server = b[idx]
    link = '{}://{}.file-upload.download:183/d/{}/video.mp4'.format(
        scheme, server, secret)

    logging.debug('Getting the video from %s', link)
    try:
        response = requests.head(link)
    except requests.exceptions.InvalidSchema:
        return 'Failed to parse player code: {}: {}'.format(link, b)
    clength = int(response.headers['Content-Length'])
    logging.info('%s -> %s (%s)', weblink, target, humanize(clength))
    response = requests.get(link, stream=True)
    t = tqdm(total=clength, unit='iB', unit_scale=True)
    block_size = 1024
    if response and response.status_code == 200:
        with open(target, 'wb') as vid:
            for block in response.iter_content(block_size):
                vid.write(block)
                t.update(len(block))
            vid.close()
            t.close()
        if clength != os.path.getsize(target):
            return 'Incorrect size downloaded. Expected: {} Received: {}'.format(
                clength, os.path.getsize(target))
    else:
        return 'Failed to retrieve video at {}: {}'.format(
            link, response.status_code)
    return None


def download_flash_file(weblink):
    """ Download video from flash-files.com """
    u = urlparse(weblink)
    code = u.path.strip('/')
    target = code + '.mp4'

    if os.path.exists(target):
        return '{} already exists. Skipping.'.format(target)

    response = requests.get(weblink)
    if not response:
        return 'GET {} failed: {}'.format(weblink, response.status_code)
    logging.debug('Retrieved %s', weblink)
    soup = BeautifulSoup(response.text, features='html.parser')
    tag = soup.find('div', id='panel4')
    if not tag:
        return 'No panel4 div in {}'.format(weblink)
    name = tag.find('textarea').find('a').text
    logging.info('Title %s', name)

    data = {}
    data.update({'p': name})
    data.update({'h': code})
    data.update({'websitereferer': 'websitereferer'})
    embed_link = '{}://{}/downloadfile.php'.format(u.scheme, u.netloc)
    logging.debug('Posting %s to %s', data, embed_link)
    response = requests.post(embed_link, data=data)
    if response:
        logging.info('%s -> %s', weblink, target)
        with open(target, 'wb') as fp:
            fp.write(response.content)
            fp.close()
    else:
        return 'Failed to retrieve content at {}'.format(weblink)

    return None


def download_indishare(weblink):
    """ Download files from indishare """
    u = urlparse(weblink)
    code = u.path.strip('/')
    target = code + '.mp4'

    if os.path.exists(target):
        return '{} already exists. Skipping.'.format(target)

    response = requests.get(weblink, headers=headers)
    if not response:
        return 'GET {} failed: {}'.format(weblink, response.status_code)

    if response.status_code == requests.codes.found:
        weblink = response.headers['location']
        logging.info('Redirect to %s', weblink)

    response = requests.get(weblink, headers=headers)
    if not response:
        return 'GET {} failed: {}'.format(weblink, response.status_code)

    logging.debug('Retrieved %s', weblink)
    soup = BeautifulSoup(response.text, features='html.parser')
    form = soup.find('form')
    # http://i64.indiworlds.com:182/d/5aigdgme7db4joaxyudfxmvi2orf5bdawjtkvmaetxhiez74tl32szeqq2hyjvrzenm7ywjr/_y%20Jazz%202-Riya%20Sen.avi
    if not form:
        return 'Form not found on {}'.format(weblink)
    params = {}
    for inp in form.findAll('input'):
        params.update({inp['name']: inp['value']})
    response = requests.request(method=form['method'],
                                url=weblink,
                                params=params)
    if not response:
        return 'Unable to submit form at {}'.format(weblink)

    if response:
        print(response.status_code)
        print(response.headers)
        print(response.text)
    return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--verbose', action='store_true')
    args, urls = parser.parse_known_args()

    log_level = logging.ERROR
    if args.debug:
        log_level = logging.DEBUG
    elif args.verbose:
        log_level = logging.INFO
    logging.basicConfig(level=log_level, format='%(levelname)s %(message)s')

    ua = UserAgent()
    headers = {'User-Agent': ua.random}

    for url in urls:
        if 'www.file-up.org' in url:
            error = download_file_up(url)
            if error:
                logging.error(error)
                sys.exit(1)
        elif 'flash-files.com' in url:
            error = download_flash_file(url)
            if error:
                logging.error(error)
                sys.exit(1)
        elif 'indishare.in' in url:
            error = download_indishare(url)
            if error:
                logging.error(error)
                sys.exit(1)
        else:
            logging.error('Cannot handle %s as of now.', url)
            sys.exit(1)
            # http://shortearn.eu/YrbNn1L
