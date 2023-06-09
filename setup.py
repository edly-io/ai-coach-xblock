"""Setup for ai_coach XBlock."""


import os

from pathlib import Path
from setuptools import setup


this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()


def package_data(pkg, roots):
    """Generic function to find package_data.

    All of the files under each of the `roots` will be declared as package
    data for package `pkg`.

    """
    data = []
    for root in roots:
        for dirname, _, files in os.walk(os.path.join(pkg, root)):
            for fname in files:
                data.append(os.path.relpath(os.path.join(dirname, fname), pkg))

    return {pkg: data}


setup(
    name='ai-coach-xblock',
    version='1.0.1',
    description="AI Coach Xblock evaluates open response answer of a question using Open AI",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/edly-io/ai-feedback-xblock',
    license='AGPL v3',
    author='edly',
    packages=[
        'ai_coach',
    ],
    install_requires=[
        'XBlock',
        'openai',
        'xblock-utils'
    ],
    entry_points={
        'xblock.v1': [
            'ai_coach = ai_coach:AICoachXBlock',
        ]
    },
    package_data=package_data("ai_coach", ["static", "public"]),
)
