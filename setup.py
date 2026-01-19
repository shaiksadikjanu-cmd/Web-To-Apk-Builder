from setuptools import setup, find_packages

setup(
    name='webtoapklib', 
    version='1.0',
    description='A library to convert websites to apk files',
    author='shaik janu',
    packages=find_packages(),  
    include_package_data=True,
    package_data={
        'webtoapklib': ['*.apk', '*.keystore'], 
    },
    install_requires=[
        'Pillow',
    ],
)