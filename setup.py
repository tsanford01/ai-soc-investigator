"""Package setup for the Security Case Investigation Agent System."""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="api-tools",
    version="0.1.0",
    description="API Tools for Security Case Investigation",
    author="Codeium",
    author_email="support@codeium.com",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/security-case-investigation",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "aiohttp",
        "pydantic",
        "pydantic-settings",
        "python-dotenv",
        "requests",
        "tenacity",
        "supabase",
        "slack-sdk"
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-asyncio",
            "pytest-mock",
            "pytest-cov"
        ]
    }
)
