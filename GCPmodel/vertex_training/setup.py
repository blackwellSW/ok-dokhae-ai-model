from setuptools import setup, find_packages

setup(
    name="gemma-classical-trainer",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "torch==2.4.0",
        "transformers==4.44.2",
        "peft==0.12.0",
        "trl==0.9.6",
        "bitsandbytes==0.43.3",
        "datasets==2.21.0",
        "accelerate==0.33.0",
        "google-cloud-storage",
        "huggingface-hub",
    ],
    python_requires=">=3.10",
)
