import argparse
import gzip
import itertools
import os
import sys
import textwrap
from base64 import a85decode, a85encode
from math import ceil
from tempfile import TemporaryFile

import img2pdf
from PIL import Image, ImageDraw, ImageFont
from qrcode import QRCode
from qrcode.constants import *
from qrcode.util import BIT_LIMIT_TABLE

from pack import FileSlice

MAX_LEVEL = 24
SIZE_LIMIT_ERR_CORR = {
    ERROR_CORRECT_L: int(BIT_LIMIT_TABLE[ERROR_CORRECT_L][23] / 8),
    ERROR_CORRECT_M: int(BIT_LIMIT_TABLE[ERROR_CORRECT_M][23] / 8),
    ERROR_CORRECT_Q: int(BIT_LIMIT_TABLE[ERROR_CORRECT_Q][23] / 8),
    ERROR_CORRECT_H: int(BIT_LIMIT_TABLE[ERROR_CORRECT_H][23] / 8)
}
REMARK_LEN_LIMIT = 250
REMARK_FONT_SIZE = 20
IMAGE_SIZE = (230, 230)
IMAGE_TEXT_AREA_HEIGHT = 20
START_X = 80
START_Y = 180
END_X = 80
END_Y = 120
MARGIN_X = 30
MARGIN_Y = 30
PAGE_SIZE = (1190, 1684)
REMARK_TEXT_START_COORD = (100, 80)
FOOTER_TEXT_START_COORD = (100, 1570)
PAGE_IMAGE_COORD = [(y, x) for x, y in itertools.product(
    range(START_Y, PAGE_SIZE[1] - IMAGE_SIZE[1] - END_Y, MARGIN_Y + IMAGE_SIZE[1]),
    range(START_X, PAGE_SIZE[0] - IMAGE_SIZE[0] - END_X, MARGIN_X + IMAGE_SIZE[0]),
)]

IMAGE_PER_PAGE = len(PAGE_IMAGE_COORD)


# {1: 1094, 0: 860, 3: 614, 2: 464}

def file_to_slice(filename, content, error_correction, compress):
    if type(content) == str:
        content = content.encode('utf8')
    if len(filename) > 255:
        raise ValueError('Filename too long, should be at most 255 bytes')
    if compress:
        content = gzip.compress(content)
    content = a85encode(content).decode('ascii')
    print('Total', len(content), 'bytes of data to encode in QR code')
    slice_max_len = SIZE_LIMIT_ERR_CORR[error_correction] - (FileSlice.HEADER_FIXED_LEN + len(filename))
    file_slices = list()
    i = 0
    bp = 0
    total_slices = ceil(len(content) / slice_max_len)
    # tha max can be recomputed to balance
    slice_max_len = ceil(len(content) / total_slices)
    while bp < len(content):
        file_slices.append(FileSlice(total_slices, i, compress, content[bp:bp + slice_max_len], filename))
        bp += slice_max_len
        i += 1
    return file_slices


def slice_to_file(slices):
    filename = slices[0].filename
    total = slices[0].total
    compressed = slices[0].compressed
    contents = [None] * total

    for s in slices:
        content = s.content
        if s.filename != filename:
            raise Exception('Filename mismatch!')
        contents[s.index] = content
    if None in contents:
        raise Exception('Missing file slice(s)!')
    content = ''.join(contents)
    content = a85decode(content)

    if compressed:
        content = gzip.decompress(content)
    # decode and return
    return filename, content


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', type=str, help='File you want to convert, or text file to restore original file')
    parser.add_argument('--store', action='store_true', default=False)
    parser.add_argument('--restore', action='store_true', default=False)
    parser.add_argument('--output', type=str, help='Output file location')
    parser.add_argument('--error-correction', type=str, choices=['L', 'M', 'Q', 'H'], default='M',
                        help='Error correction level. Can be chosen from "L"(Low), "M"(Medium), '
                             '"Q"(Quarter) or "H"(High). ')
    parser.add_argument('--compress', action='store_true')
    parser.add_argument('--remark', type=str, help='Remark to put on generated page (limited to 200 characters)')
    args = parser.parse_args()
    filename = args.filename
    print('Input file:', filename)
    if len(os.path.basename(filename)) > 80:
        print('File name too long! Should be less that 70 characters.')
        sys.exit(1)
    output_filename = args.output

    error_correction = {
        'L': ERROR_CORRECT_L,
        'M': ERROR_CORRECT_M,
        'Q': ERROR_CORRECT_Q,
        'H': ERROR_CORRECT_H
    }[args.error_correction]
    if args.store and not args.restore:
        compress = args.compress
        if not output_filename:
            output_filename = os.path.basename(filename) + '.pdf'
        if not output_filename.endswith('.pdf'):
            output_filename = output_filename + '.pdf'
        remark = os.path.basename(filename)
        if args.remark:
            if len(args.remark) > REMARK_LEN_LIMIT:
                sys.stderr.write('Remark too long!\n')
                sys.exit(1)
            remark += (' ' + args.remark)
        store_to_qr(filename, output_filename, remark, error_correction, compress)
    elif args.restore:
        qr_content_to_file(filename, output_filename)

    else:
        print('Error: Please specify --store or --restore')
        sys.exit(1)
    print('Done!')


def qr_content_to_file(filename, output_filename):
    restored_slices = list()
    with open(filename, encoding='utf8') as f:
        for line in f:
            if not line:
                continue
            slice = FileSlice.deserialize(line.strip())
            restored_slices.append(slice)
    filename, content = slice_to_file(restored_slices)
    if not output_filename:
        name, suffix = os.path.splitext(filename)
        output_filename = name + '_restore' + suffix
    print('Convert paper to file, output to', output_filename)
    with open(output_filename, 'wb') as f:
        f.write(content)


def store_to_qr(filename, output_filename, remark, error_correction, compress):
    para = textwrap.wrap(remark, width=100)
    print('Convert file to paper, output to', output_filename)
    with open(filename, 'rb') as f:
        content = f.read()
    slices = file_to_slice(os.path.basename(filename), content, error_correction, compress)
    page_count = ceil(len(slices) / IMAGE_PER_PAGE)
    qr_counter = 0
    print('Generating PDF,', page_count, 'pages in total')
    page_images = list()
    temp_files = list()
    for i in range(page_count):
        page_image = Image.new('1', PAGE_SIZE, color='white')
        text_draw = ImageDraw.Draw(page_image)
        font = ImageFont.truetype('arial.ttf', REMARK_FONT_SIZE)
        text_draw.text(FOOTER_TEXT_START_COORD, os.path.basename(filename), font=font)
        text_draw.text((FOOTER_TEXT_START_COORD[0], FOOTER_TEXT_START_COORD[1] + REMARK_FONT_SIZE),
                       'Page {}/{}'.format(i + 1, page_count), font=font)

        for n, line in enumerate(para):
            text_draw.text((REMARK_TEXT_START_COORD[0], REMARK_TEXT_START_COORD[1] + REMARK_FONT_SIZE * n), line,
                           font=font)
        for j in range(min(IMAGE_PER_PAGE, len(slices) - IMAGE_PER_PAGE * i)):
            qr = QRCode(error_correction=error_correction, box_size=10, border=0)
            qr.add_data(slices[i * IMAGE_PER_PAGE + j].serialize())
            extended_qr_image = Image.new('1', (IMAGE_SIZE[0], IMAGE_SIZE[1] + IMAGE_TEXT_AREA_HEIGHT),
                                          color='white')
            qr_image = qr.make_image()
            qr_image = qr_image.resize(IMAGE_SIZE)
            extended_qr_image.paste(qr_image)
            qr_text_draw = ImageDraw.Draw(extended_qr_image)
            qr_text_draw.text((10, IMAGE_SIZE[1]), '{}/{}'.format(qr_counter + 1, len(slices)), font=font)
            page_image.paste(extended_qr_image, PAGE_IMAGE_COORD[j])

            qr_counter += 1
        page_images.append(page_image)
        temp_file = TemporaryFile(suffix='.png')
        page_image.save(temp_file, format='PNG')
        temp_file.seek(0)
        temp_files.append(temp_file)
    with open(output_filename, 'wb') as f:
        img2pdf.convert(temp_files, outputstream=f)


if __name__ == '__main__':
    main()
