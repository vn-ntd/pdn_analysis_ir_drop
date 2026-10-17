from setuptools import setup, find_packages

setup(
    name="pdn_analysis",
    version="1.0.0",
    description="Power Distribution Network (PDN) Analysis, Sizing & IR-Drop Optimization in VLSI",
    author="Dung",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "numpy>=1.24.0",
        "scipy>=1.10.0",
        "matplotlib>=3.7.0",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
    ],
)
