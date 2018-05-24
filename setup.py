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
    project_urls={
        'Source Code': 'https://github.com/mobiusklein/psims',
        'Issue Tracker': 'https://github.com/mobiusklein/psims/issues'
    },
)
