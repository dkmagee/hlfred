from setuptools import setup

setup(
    name='hlfred',
    version='0.1',
    packages=['hlfred', 'hlfred.commands', 'hlfred.tasks', 'hlfred.utils'],
    include_package_data=True,
    install_requires=[
        'Click',
    ],
    entry_points='''
        [console_scripts]
        hlfred=hlfred.cli:cli
    ''',
)