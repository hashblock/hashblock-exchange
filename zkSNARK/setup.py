
from setuptools import setup

setup(
    name='hashblock_zksnark',
    version='0.1.0',  # specified elsewhere
    packages=['hashblock_zksnark'],
    package_dir={'hashblock_zksnark': '/hashblock-exchange/zkSNARK/hashblock_zksnark'},
    package_data={'hashblock_zksnark': ['hashblock_zksnark.so']},
)
