Test agx.generator.zca
======================

Setup configuration and emulate main routine::

    >>> from zope.configuration.xmlconfig import XMLConfig

    >>> import agx.core
    >>> XMLConfig('configure.zcml', agx.core)()

    >>> from agx.core.main import parse_options

    >>> import os
    >>> modelpath = os.path.join(datadir, 'agx.generator.sql-sample.uml')

    >>> import pkg_resources
    >>> subpath = 'profiles/pyegg.profile.uml'
    >>> eggprofilepath = \
    ...     pkg_resources.resource_filename('agx.generator.pyegg', subpath)

    >>> subpath = 'profiles/zca.profile.uml'
    >>> zcaprofilepath = \
    ...     pkg_resources.resource_filename('agx.generator.zca', subpath)

    >>> subpath = 'profiles/sql.profile.uml'
    >>> sqlprofilepath = \
    ...     pkg_resources.resource_filename('agx.generator.sql', subpath)

    >>> modelpaths = [modelpath, eggprofilepath, zcaprofilepath, sqlprofilepath]

    >>> outdir = os.path.join(datadir, 'agx.generator.sql-sample')
    >>> controller = agx.core.Controller()
    >>> target = controller(modelpaths, outdir)
    >>> target
    <Directory object '/.../agx.generator.sql/src/agx/generator/sql/testing/data/agx.generator.sql-sample' at ...>
