import argparse

def main():

    parser = argparse.ArgumentParser(
        prog="embed_file",
        description="Embed raw file contents as a freezable python module")
    parser.add_argument("file", help="Name of file to embed")

    args = parser.parse_args()

    with open(args.file, "rb") as f:
        data = f.read()

    print("_data =\\", sep='')
    print("b'", sep='', end='')

    for i in range(0, len(data), 16):
        line = data[i:i+16]
        if i and i % 16 == 0:
            print("'\\\nb'", end='', sep='')

        for b in line:
            print(f"\\x{b:02x}", sep='', end='')

    print("'\nDATA = memoryview(_data)")

main()
