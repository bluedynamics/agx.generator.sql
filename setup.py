import os
from setuptools import (
    setup,
    find_packages,
)


version = "1.0a1"
shortdesc = "AGX generator for sqlalchemy"
longdesc = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read()
longdesc += open(os.path.join(os.path.dirname(__file__), 'LICENSE.rst')).read()


setup(name="agx.generator.sql",
      version=version,
      description=shortdesc,
      long_description=longdesc,
      classifiers=[
          'Development Status :: 3 - Alpha',
          'License :: OSI Approved :: GNU General Public License (GPL)',
          'Programming Language :: Python',
      ],
      keywords="AGX, Code Generation",
      author="BlueDynamics Alliance",
      author_email="dev@bluedynamics.com",
      url="http://github.com/bluedynamics/agx.generator.sql",
      license="GNU General Public Licence",
      packages=find_packages("src"),
      package_dir={"": "src"},
      namespace_packages=["agx", "agx.generator"],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'interlude', 
          'agx.generator.pyegg',
          ##code-section dependencies
          ##/code-section dependencies
      ],
      extras_require = dict(
          ##code-section extras_require
          test=[
            'interlude',
          ]

          ##/code-section extras_require
      ),
      entry_points="""
      ##code-section entry_points
      [agx.generator]
      register = agx.generator.sql:register
      ##/code-section entry_points
      """,
      ##code-section additionals
      ##/code-section additionals
      )
