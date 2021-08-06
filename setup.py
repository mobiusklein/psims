from setuptools import find_packages, setup


with open("psims/version.py") as version_file:
    version = None
    for line in version_file.readlines():
        if "version = " in line:
            version = line.split(" = ")[1].replace("\"", "").replace("'", "").strip()
            print("Version is: %r" % (version,))
            break
    else:
        print("Cannot determine version")

long_description = ''
try:
    with open("README.md", 'r') as fh:
        long_description = fh.read()
except Exception:
    print("long_description is missing")


extras_require = {
    'mzmlb': ['h5py', 'hdf5plugin'],
    'numpress': ['pynumpress']
}
extras_require['all'] = sum(extras_require.values(), [])

setup(
    name='psims',
    version=version,
    description="Writers and controlled vocabulary manager for PSI-MS's mzML and mzIdentML standards",
    long_description=long_description,
    long_description_content_type='text/markdown',
    maintainer='Joshua Klein',
    maintainer_email="jaklein@bu.edu",
    zip_safe=False,
    packages=find_packages(),
    url="https://github.com/mobiusklein/psims",
    include_package_data=True,
    package_data={
        "psims.controlled_vocabulary": ["psims/controlled_vocabulary/vendor/*"],
        "psims.validation": ["psims/validation/xsd/*"]
    },
    install_requires=[
        "lxml",
        "six",
        "sqlalchemy",
        "numpy"
    ],
    extras_require=extras_require,
    project_urls={
        'Source Code': 'https://github.com/mobiusklein/psims',
        'Issue Tracker': 'https://github.com/mobiusklein/psims/issues'
    },
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Topic :: Text Processing :: Markup :: XML",
        "Intended Audience :: Science/Research",
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ]
)
