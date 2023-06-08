"""Setup for ai_coach XBlock."""


import os

from setuptools import setup


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
    name='ai_coach-xblock',
    version='0.1',
    description='ai_coach XBlock',
    license='AGPL v3',
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
