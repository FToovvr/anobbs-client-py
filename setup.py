import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="anobbs-client",
    version="0.0.0",
    author="FToovvr",
    author_email="FToovvr@protonmail.com",
    description="Simple AnoBBS API wrapper",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/FToovvr/anobbs-api-wrapper-py",
    packages=setuptools.find_packages(exclude=("test",)),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 2 - Pre-Alpha",
        "Natural Language :: Chinese (Simplified)",
    ],
    python_requires='>=3.8',
    install_requires=[
        "python-dateutil>=2.8.1",
        "requests>=2.24",
        "requests-toolbelt>=0.9.1",
    ],
)
