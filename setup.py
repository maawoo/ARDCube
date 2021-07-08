from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()
long_description = (here / 'README.md').read_text(encoding='utf-8')

setup(
    name='ARDCube',
    version='0.1.0',
    description="Utility to create Analysis Ready (Earth Observation) Data Cubes",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url="https://github.com/maawoo/ARDCube",
    author="Marco Wolsza",
    author_email="marco.wolsza@uni-jena.de",
    license='MIT',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3 :: Only'],
    packages=find_packages(where='.'),
    include_package_data=True,
    install_requires=open("requirements.txt").read().splitlines(),
    zip_safe=False,
    entry_points={
        'console_scripts': ['ardcube=ARDCube.cli:cli']
    }
)
