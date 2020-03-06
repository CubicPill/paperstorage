HEADER = b'PS'


class DeserializationError(Exception):
    pass


class FileSlice:
    """
    packet format:
    'PS'(header, 2bytes)+total(1byte, 1-255)+index(1byte, 0-254)+compressed(1byte,bool)
    +filename_length(1 byte,1-255)+filename(up to 255 bytes)
    +content_length(2 bytes,1-65535)+content(typically less than 3000 bytes)

    """
    HEADER_FIXED_LEN = 7

    def __init__(self, total, index, compressed, content: bytes or str, filename: str = None):
        self.total = total
        self.index = index
        self.compressed = compressed
        if type(content) == str:
            content = content.encoode('utf8')
        self.content = content
        self.filename = filename

    def serialize(self):
        data = b''
        data += HEADER
        data += bytes([self.total, self.index])
        data += bytes([int(self.compressed)])
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
        total, index = data[:2]
        data = data[2:]
        compressed = bool(data[0])
        data = data[1:]
        filename_len = data[0]
        filename = data[1:filename_len + 1].decode('utf8')
        data = data[filename_len + 1:]

        content_length = int.from_bytes(data[:2], byteorder='big', signed=False)
        content = data[2:]
        if len(content) != content_length:
            raise DeserializationError('Incorrect content length, expected {}, got {}'.format(content_length,len(content)))
        return FileSlice(total, index, compressed, content, filename)


if __name__ == '__main__':
    q = FileSlice(2, 1, False, b'12312312313', '123.txt')
    d = q.serialize()
    print(d)
    q = FileSlice.deserialize(d)
    d = q.serialize()
    print(d)
    q = FileSlice.deserialize(d)
    d = q.serialize()
    print(d)
    q = FileSlice.deserialize(d)
    d = q.serialize()
    print(d)
    q = FileSlice.deserialize(d)
    d = q.serialize()
    print(d)
    q = FileSlice.deserialize(d)
