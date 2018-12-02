import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="once_again",
    version="1.0",
    author="Dmitrii Borisevich",
    author_email="borisevichdi@gmail.com",
    description="Decorator for making reproducible function calls",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/borisevichdi/once-again",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
)
