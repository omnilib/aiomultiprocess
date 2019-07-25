from setuptools import setup

with open("README.md") as f:
    readme = f.read()

with open("aiomultiprocess/__init__.py") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split('"')[1]

setup(
    name="aiomultiprocess",
    description="asyncio version of the standard multiprocessing module",
    long_description=readme,
    long_description_content_type="text/markdown",
    version=version,
    author="John Reese",
    author_email="john@noswap.com",
    url="https://github.com/jreese/aiomultiprocess",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: AsyncIO",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Software Development :: Libraries",
    ],
    license="MIT",
    packages=["aiomultiprocess", "aiomultiprocess.tests"],
    python_requires=">=3.6",
    setup_requires=["setuptools>=38.6.0"],
    install_requires=[],
)
