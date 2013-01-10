# -*- coding: utf-8 -*-
import generator


def register():
    """Register this generator.
    """
    import agx.generator.sql
    from agx.core.config import register_generator
    register_generator(agx.generator.sql)
