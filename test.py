import sys

if __name__ == "__main__":
    ret_code = int(sys.argv[1])
    print(f"Got {ret_code} returning code!")
    sys.exit(ret_code)