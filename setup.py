from setuptools import setup, find_packages

setup(
    name="AuroCC",
    version="0.1",
    packages=find_packages(),
    package_data={
        '': ['*.db', '*.yml','*.index','*.pkl'],
    },
    include_package_data=True,
)
