from setuptools import setup

with open("requirements.txt") as f:
    packages = f.read().splitlines()

setup(
    name="autocoder",
    version="0.1.0",
    description="Automatically creating functions that LLMs can use..",
    author="Thomas Tumiel",
    packages=["autocoder"],
    license="MIT",
    install_requires=packages,
    python_requires=">=3.7",
    extras_require={
        "dev": ["pytest", "black", "isort", "pytest-cov"],
        "server": ["Flask>=2.3.3", "Flask-Cors>=4.0.0"],
    },
)
