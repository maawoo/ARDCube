from setuptools import setup, find_packages
from io import open

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name='ARDCube',
    version='0.1.0',
    description="Utility to create Analysis Ready (Earth Observation) Data Cubes",
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python'],
    packages=find_packages(),
    include_package_data=True,
    install_requires=open("requirements.txt").read().splitlines(),
    author="Marco Wolsza",
    author_email="marco.wolsza@uni-jena.de",
    url="https://github.com/maawoo/ARDCube",
    license='MIT',
    zip_safe=False,
    entry_points={
        'console_scripts': ['ardcube=ARDCube.cli:cli']
    }
)