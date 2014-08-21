from setuptools import setup, find_packages

setup(
    name = 'epmc_retrieve',
    version = '0.1',
    packages = find_packages(),
    install_requires = [
        "requests"
    ]
)
