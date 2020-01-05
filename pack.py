HEADER = b'PS'


class DeserializationError(Exception):
    pass


class QRPackage:
    """
    packet format:
    'PS'(header, 2bytes)+total(1byte, 1-255)+index(1byte, 0-254)
    +optional, if index==0[filename_length(1 byte,1-255)+filename(up to 255 bytes)]
    +content_length(2 bytes,1-65535)+content(typically less than 3000 bytes)

    """

    def __init__(self, total, index, content: bytes or str,  filename:str=None):
        self.total = total
        self.index = index
        if type(content) == str:
            content = content.encoode('utf8')
        self.content = content

        self.is_first = index==0
        self.filename = filename

    def serialize(self):
        data = b''
        data += HEADER
        data += bytes([self.total, self.index])
        if self.is_first:
            data += bytes([len(self.filename)])
            data += bytes(self.filename, encoding='utf8')
        data += (len(self.content)).to_bytes(2, byteorder='big', signed=False)
        data += self.content
        return data

    @classmethod
    def deserialize(cls, data: bytes):
        if not data.startswith(HEADER):
            raise DeserializationError('Invalid header')
        data = data[2:]
        total, index= data[:2]
        data = data[2:]
        filename = ''
        is_first=index==0
        if bool(is_first):
            filename_len = data[0]
            filename = data[1:filename_len + 1].decode('utf8')
            data = data[filename_len + 1:]

        content_length = int.from_bytes(data[:2],byteorder='big', signed=False)
        content = data[2:]
        if len(content) != content_length:
            raise DeserializationError('Incorrect content length')
        return QRPackage(total, index, content,  filename)


if __name__ == '__main__':
    q = QRPackage(10, 0, b'12312312313', '123.txt')
    d = q.serialize()
    print(d)
    q = QRPackage.deserialize(d)
    d = q.serialize()
    print(d)
    q = QRPackage.deserialize(d)
    d = q.serialize()
    print(d)
    q = QRPackage.deserialize(d)
    d = q.serialize()
    print(d)
    q = QRPackage.deserialize(d)
    d = q.serialize()
    print(d)
    q = QRPackage.deserialize(d)
