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

setup(
    name='psims',
    version=version,
    description="Writers and controlled vocabulary manager for PSI-MS's mzML and mzIdentML standards",
    maintainer='Joshua Klein',
    maintainer_email="jaklein@bu.edu",
    zip_safe=False,
    packages=find_packages(),
    url="https://github.com/mobiusklein/psims",
    include_package_data=True,
    install_requires=[
        "lxml",
        "six",
        "sqlalchemy",
        "numpy"
    ]
)
