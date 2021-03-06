from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(name='alain',
      version=version,
      description="Alain",
      long_description="""\
AFPy's IRC bot""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='irc afpy',
      author='Gael Pasgrimaud',
      author_email='gawel@afpy.org',
      url='https://hg.afpy.org/gawel/alain/index.html',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-
      [console_scripts]
      alain = alain.main:main
      """,
      )
