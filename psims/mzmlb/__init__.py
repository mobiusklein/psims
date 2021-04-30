try:
    from .writer import MzMLbWriter
except ImportError as err:
    class MzMLbWriter(object):
        def __init__(self, *args, **kwargs):
            import warnings
            warnings.warn(
                "The mzMLb component requires h5py and hdf5plugin to function. "
                "Please install them directly, or with `pip install psims[mzmlb]`")
            raise err
