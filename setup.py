from setuptools import setup, find_packages
from sentry_defcon import VERSION

setup(
    name='sentry_defcon',
    version=VERSION,
    author='Tommaso Barbugli',
    author_email='tbarbugli@gmail.com',
    url='http://github.com/tbarbugli/sentry_defcon',
    description='A plugin to have defcon condition status visible',
    long_description='',
    packages=find_packages(),
    install_requires=['sentry'],
    test_suite='runtests.runtests',
    license='BSD',
    include_package_data=True,
    classifiers=[
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Topic :: Software Development'
    ],
)
