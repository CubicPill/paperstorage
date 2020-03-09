HEADER = 'PS'


class DeserializationError(Exception):
    pass


class FileSlice:
    """
    packet format:
    'PS'(header, 2bytes)+total(3bytes, 001-999 text)+index(3bytes, 000-998 text)+compressed(1byte,0 or 1 text)
    +filename_length(2 bytes,01-99 text)+filename(up to 99 bytes str)
    +content_length(4 bytes,0000-9999 str)+content(typically less than 3000 bytes)

    """
    HEADER_FIXED_LEN = 15

    def __init__(self, total, index, compressed, content: str, filename: str = None):
        self.total = total
        self.index = index
        self.compressed = compressed
        if type(content) != str:
            raise TypeError
        self.content = content
        self.filename = filename

    def serialize(self):
        data = HEADER + '{total:03d}{index:03d}{compressed:01d}{filename_len:02d}{filename}{content_len:04d}{content}'.format(
            total=self.total,
            index=self.index,
            compressed=self.compressed,
            filename_len=len(self.filename),
            filename=self.filename,
            content_len=len(self.content),
            content=self.content
        )
        return data

    @classmethod
    def deserialize(cls, data: str):
        if type(data) != str:
            raise TypeError
        if not data.startswith(HEADER):
            raise DeserializationError('Invalid header')

        data = data[2:]
        total = int(data[:3])
        data = data[3:]
        index = int(data[:3])
        data = data[3:]
        compressed = bool(int(data[0]))
        data = data[1:]
        filename_len = int(data[:2])
        data = data[2:]
        filename = data[:filename_len]
        data = data[filename_len:]
        content_length = int(data[:4])
        content = data[4:]
        if len(content) != content_length:
            raise DeserializationError(
                'Incorrect content length, expected {}, got {}'.format(content_length, len(content)))
        return FileSlice(total, index, compressed, content, filename)


if __name__ == '__main__':
    q = FileSlice(2, 1, False, '12312312313', '123.txt')
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
