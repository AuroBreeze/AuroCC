from setuptools import setup, find_packages

setup(
    name="AuroCC",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'websockets',
        'aiohttp',
        'openai',
    ],
    package_data={
        '': ['*.db', '*.yml'],
    },
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'aurocc=main:main',
        ],
    },
)
