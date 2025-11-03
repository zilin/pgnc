from setuptools import setup, find_packages

setup(
    name="pgn-curator",
    version="0.1.0",
    description="Config-driven chess opening repertoire curation tool",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Chess Opening Trainer Team",
    url="https://github.com/yourusername/pgnc",
    packages=find_packages(),
    install_requires=[
        "chess>=1.10.0",
        "click>=8.1.0",
        "pyyaml>=6.0",
        "pydantic>=2.0.0",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "pgnc=pgnc.cli:cli",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Games/Entertainment :: Board Games",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
