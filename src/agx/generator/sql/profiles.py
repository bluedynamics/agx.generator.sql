# -*- coding: utf-8 -*-
from zope.interface import implements
from agx.core.interfaces import IProfileLocation
import agx.generator.sql

class ProfileLocation(object):

    implements(IProfileLocation)
    name = u'sql.profile.uml'
    package = agx.generator.sql