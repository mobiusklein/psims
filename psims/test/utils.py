import os


test_root = os.path.abspath(os.path.dirname(__file__))


def find_test_file(name):
    return os.path.join(test_root, name)
