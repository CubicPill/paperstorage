from qrcode import QRCode
from qrcode.constants import *
import pdfrw
from qrcode.util import BIT_LIMIT_TABLE

import sys

import argparse


def file_to_qr(filename, content):
    pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', type=str, help='File you want to convert')
    parser.add_argument('--error-correction', type=str, choices=['L', 'M', 'Q', 'H'], default='M')
    parser.add_argument('--compress', action='store_true')
    parser.add_argument('--output')
    qr = QRCode(error_correction=ERROR_CORRECT_M, border=1)

    img = qr.make_image()
    img.save('out.png')
    print(qr.version)

    img.show()


if __name__ == '__main__':
    main()
