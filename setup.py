from setuptools import find_packages, setup


setup(
    name='psims',
    version='0.0.6',
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
