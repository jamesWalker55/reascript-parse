def info(fmt: str, *args):
    print("[INFO] {}".format(fmt.format(*args)))


def warn(fmt: str, *args):
    print("[WARN] {}".format(fmt.format(*args)))


def error(fmt: str, *args):
    print("[ERROR] {}".format(fmt.format(*args)))
