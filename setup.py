from setuptools import setup

setup(
    name='web_to_apk_tool',
    version='1.0',
    description='A library to convert websites to apk files ',
    author='shaik janu',
    py_modules=['apk_builder'],
    include_package_data=True,   
    install_requires=[
        'Pillow',
    ],
)