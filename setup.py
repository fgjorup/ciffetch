from pathlib import Path

from setuptools import setup


ROOT = Path(__file__).parent


def readme():
    """Read the project README for the package description."""
    return (ROOT / "README.md").read_text(encoding="utf-8")


setup(
    name="ciffetch",
    version="0.1.0",
    description="A PyQt dialog for searching COD and fetching CIF files",
    long_description=readme(),
    long_description_content_type="text/markdown",
    author="Frederik H Gjørup",
    author_email="fgjorup@chem.au.dk",
    url="https://github.com/fgjorup/ciffetch",
    license="GPL-3.0-only",
    py_modules=["ciffetch"],
    install_requires=[
        "PyQt6>=6.8.1",
        "requests>=2.25.0",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
    ],
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "ciffetch=ciffetch:main",
        ],
    },
)
