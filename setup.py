from setuptools import setup

setup(
    name="autocoder",
    version="0.1.0",
    description="Automatically creating functions that LLMs can use.",
    long_description=open("README.md").read(),
    long_description_content_type='text/markdown',
    author="Thomas Tumiel",
    packages=["autocoder"],
    license="MIT",
    install_requires=["docstring-parser", "pydantic"],
    python_requires=">=3.7",
    url="https://github.com/ttumiel/autocoder",
    extras_require={
        "test": ["pytest", "black", "isort", "pytest-cov"],
        "server": ["Flask", "Flask-Cors", "PyYAML"],
        "api": ["openai"],
        "deploy": ["functions-framework"],
    },
)
