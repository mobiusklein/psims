from setuptools import find_packages, setup


setup(
    name='psims',
    version='0.0.2',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "lxml",
        "six",
        "sqlalchemy"
    ]
)
