import os


data_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__)))


def datafile(name):
    return os.path.join(data_path, name)
