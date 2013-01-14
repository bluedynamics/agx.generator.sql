# -*- coding: utf-8 -*-
from zope.interface import implementer
from agx.core.interfaces import IProfileLocation
import agx.generator.sql


@implementer(IProfileLocation)
class ProfileLocation(object):
    name = u'sql.profile.uml'
    package = agx.generator.sql
