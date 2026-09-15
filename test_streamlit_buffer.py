import io

class MockUploadedFile(io.BytesIO):
    def __init__(self, data):
        super().__init__(data)
        self.name = "test.png"

f = MockUploadedFile(b"fake image data")

# write first time
path1 = "test1.png"
with open(path1, "wb") as out1:
    out1.write(f.getbuffer())

# write second time
path2 = "test2.png"
with open(path2, "wb") as out2:
    out2.write(f.getbuffer())

with open(path1, "rb") as in1:
    print("test1.png length:", len(in1.read()))

with open(path2, "rb") as in2:
    print("test2.png length:", len(in2.read()))
