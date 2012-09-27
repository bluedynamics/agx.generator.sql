# -*- coding: utf-8 -*-
from agx.core import Scope

class SqlContentScope(Scope):

    def __call__(self, node):
        return node.stereotype('sql:sql_content') is not None

class SqlConcreteTableInheritanceScope(Scope):

    def __call__(self, node):
        return node.stereotype('sql:sql_content') is not None \
            and node.stereotype('sql:concrete_table_inheritance') is not None

class SqlJoinedTableInheritanceScope(Scope):

    def __call__(self, node):
        return node.stereotype('sql:sql_content') is not None \
            and node.stereotype('sql:joined_table_inheritance') is not None

class SqlTableScope(Scope):

    def __call__(self, node):
        return node.stereotype('sql:sql_table') is not None

class SqlSAConfigScope(Scope):

    def __call__(self, node):
        return node.stereotype('sql:z3c_saconfig') is not None
