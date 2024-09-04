import os
from glob import glob
from setuptools import setup
from setuptools import find_packages

package_name = 'd37pxi_unity'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        # ('share/ament_index/resource_index/packages',['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),glob('launch/*.launch')),
        (os.path.join('share', package_name, 'launch'),glob('launch/*launch.py')),
        (os.path.join('share', package_name, 'rviz2'),glob('rviz2/*.rviz')),
        (os.path.join('share', package_name, 'config'),glob('config/*.rviz')),
        (os.path.join('share', package_name, 'd37pxi_untiy'),glob('d37pxi_unity/*.py')),
 
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
        ],
    },
)
