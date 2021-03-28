try:
    from .writer import MzMLbWriter
except ImportError as err:
    class MzMLbWriter(object):
        def __init__(self, *args, **kwargs):
            raise err
