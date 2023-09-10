from setuptools import setup

with open("requirements.txt") as f:
    packages = f.read().splitlines()

setup(
    name="autocoder",
    version="0.1.0",
    packages=["autocoder"],
    install_requires=packages,
    extras_require={
        "dev": ["pytest>=7.0.0", "black>=23.0.0", "isort>=5.12.0"],
        "server": ["Flask>=2.3.3", "Flask-Cors>=4.0.0"],
    },
)
