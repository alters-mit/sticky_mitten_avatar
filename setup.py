from setuptools import setup, find_packages


setup(
    name='sticky_mitten_avatar',
    version="0.9.0",
    description='High-level API for the Sticky Mitten Avatar in TDW.',
    long_description='High-level API for the Sticky Mitten Avatar in TDW.',
    url='https://github.com/alters-mit/sticky_mitten_avatar',
    author='Seth Alter',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8'
    ],
    keywords='unity simulation tdw',
    packages=find_packages(),
    install_requires=['tdw==1.7.16.1', 'numpy', 'ikpy', 'matplotlib', 'pillow'],
)
