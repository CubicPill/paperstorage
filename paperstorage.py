import argparse
import gzip
import os
import sys
from base64 import a85decode, a85encode
from math import ceil
from tempfile import TemporaryFile

import img2pdf
import pdf2image
from PIL import Image
from qrcode import QRCode
from qrcode.constants import *
from qrcode.util import BIT_LIMIT_TABLE
from zbar import Scanner

from pack import FileSlice

MAX_LEVEL = 24
SIZE_LIMIT_ERR_CORR = {
    ERROR_CORRECT_L: int(BIT_LIMIT_TABLE[ERROR_CORRECT_L][23] / 8),
    ERROR_CORRECT_M: int(BIT_LIMIT_TABLE[ERROR_CORRECT_M][23] / 8),
    ERROR_CORRECT_Q: int(BIT_LIMIT_TABLE[ERROR_CORRECT_Q][23] / 8),
    ERROR_CORRECT_H: int(BIT_LIMIT_TABLE[ERROR_CORRECT_H][23] / 8)
}
PAGE_IMAGE_COORD = [
    (120, 122), (620, 122),
    (120, 622), (620, 622),
    (120, 1122), (620, 1122)
]


# {1: 1094, 0: 860, 3: 614, 2: 464}

def file_to_slice(filename, content, error_correction, compress):
    if type(content) == str:
        content = content.encode('utf8')
    if len(filename) > 255:
        raise ValueError('Filename too long, should be at most 255 bytes')
    if compress:
        content = gzip.compress(content)
    content = a85encode(content).decode('ascii')
    print('Total',len(content),'bytes of data to encode in QR code')
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
        assert s.filename == filename
        contents[s.index] = content
    assert None not in contents
    content = ''.join(contents)
    content = a85decode(content)

    if compressed:
        content = gzip.decompress(content)
    # decode and return
    return filename, content


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', type=str, help='File you want to convert')
    parser.add_argument('--store', action='store_true', default=False)
    parser.add_argument('--restore', action='store_true', default=False)
    parser.add_argument('--output', type=str, help='Output file location')
    parser.add_argument('--error-correction', type=str, choices=['L', 'M', 'Q', 'H'], default='M',
                        help='Error correction level. Can be chosen from "L"(Low), "M"(Medium), '
                             '"Q"(Quarter) or "H"(High). ')
    parser.add_argument('--compress', action='store_true')
    args = parser.parse_args()
    filename = args.filename
    print('Input file:', filename)
    if len(filename) > 80:
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
        if not output_filename:
            output_filename = os.path.basename(filename) + '.pdf'
        if not output_filename.endswith('.pdf'):
            output_filename = output_filename + '.pdf'
        print('Convert file to paper, output to', output_filename)
        with open(filename, 'rb') as f:
            content = f.read()
        slices = file_to_slice(os.path.basename(filename), content, error_correction, args.compress)
        page_count = ceil(len(slices) / 6)
        print('Generating PDF,',page_count,'pages in total')
        page_images = list()
        temp_files = list()
        for i in range(page_count):
            page_image = Image.new('1', (1190, 1684), color='white')
            for j in range(min(6, len(slices) - 6 * i)):
                qr = QRCode(error_correction=error_correction, box_size=10, border=0)
                qr.add_data(slices[i * 6 + j].serialize())
                qr_image = qr.make_image()
                qr_image = qr_image.resize((440, 440))
                page_image.paste(qr_image, PAGE_IMAGE_COORD[j])
            page_images.append(page_image)
            temp_file = TemporaryFile(suffix='.png')
            page_image.save(temp_file, format='PNG')
            temp_file.seek(0)
            temp_files.append(temp_file)

        with open(output_filename, 'wb') as f:
            img2pdf.convert(temp_files, outputstream=f)
    elif args.restore:
        pages = pdf2image.convert_from_path(filename)
        restored_slices = list()

        for p in pages:
            p = p.convert('L')
            # scale
            h, w = p.size
            if h > 1000 or w > 1000:
                if h > w:
                    h = 1000
                    w = int(w * (h / 1000))
                else:
                    w = 1000
                    h = int(h * (w / 1000))
                p = p.resize((h, w), Image.HAMMING)

            scanner = Scanner()
            results = scanner.scan(p)
            for r in results:

                _type, data, quality, position = r
                if _type != 'QR-Code':
                    continue
                data = data.decode('ascii')
                slice = FileSlice.deserialize(data)
                restored_slices.append(slice)
        filename, content = slice_to_file(restored_slices)
        if not output_filename:
            name, suffix = os.path.splitext(filename)
            output_filename = name + '.restore' + suffix
        print('Convert paper to file, output to', output_filename)
        with open(output_filename, 'wb') as f:
            f.write(content)

    else:
        print('Error: Please specify --store or --restore')
        sys.exit(1)
    print('Done!')


if __name__ == '__main__':
    main()
