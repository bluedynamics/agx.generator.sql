# -*- coding: utf-8 -*
import os
from zope.component.interfaces import ComponentLookupError
from agx.core import (
    handler,
    Scope,
    registerScope,
    token
)
from agx.core.util import (
    read_target_node,
    dotted_path,
)

from node.ext.uml.interfaces import (
    IClass,
    IInterface,
    IInterfaceRealization,
    IDependency,
    IProperty,
)
from node.ext.python.utils import Imports

from node.ext.uml.utils import (
    TaggedValues,
    UNSET,
)
from agx.generator.pyegg.utils import (
    class_base_name,
    templatepath,
    set_copyright,
)
from node.ext.python.interfaces import (
    IClass as IPythonClass,
    IAttribute,
    IImport,
)
from node.ext.python import Attribute

from agx.generator.sql.scope import SqlContentScope, SqlTableScope

registerScope('sqlcontent','uml2fs',[IClass] ,SqlContentScope)
#registerScope('pyattribute','uml2fs',[IProperty] ,SqlContentScope)

@handler('sqlcontentclass', 'uml2fs', 'connectorgenerator',
         'sqlcontent', order=10)
def sqlcontentclass(self, source, target):
    '''sqlalchemy class'''
    targetclass = read_target_node(source, target.target)
    module=targetclass.parent
    imps=Imports(module)
    imps.set('sqlalchemy.declarative',[['declarative_base',None]])
    imps.set('sqlalchemy',[['Column',None],
                           ['Integer',None],
                           ['String',None],
                           ['ForeignKey',None]])
    
    #find last import and do some assignments afterwards
    lastimport=[imp for imp in module.filtereditems(IImport)][-1]
    globalatts=[att for att in module.filtereditems(IAttribute)]
    classatts=[att for att in targetclass.filtereditems(IAttribute)]

    #generate the Base=declarative_base() statement
    att=Attribute(['Base'],'declarative_base()')
    att.__name__='Base'
    if not [a for a in globalatts if a.targets==['Base']]:
        module.insertafter(att,lastimport)
        
    #generate the __tablename__ attribute
    if not [a for a in classatts if a.targets==['__tablename__']]:
        tablename=Attribute(['__tablename__'],"'%s'" % (source.name.lower()))
        tablename.__name__='__tablename__'
        targetclass.insertfirst(tablename)
    
    #lets inherit from Base
    if targetclass.bases==['object']:
        targetclass.bases=['Base']
    else:
        if 'Base' not in targetclass.bases:
            targetclass.bases.insert(0,'Base')
    

@handler('sqlattribute', 'uml2fs', 'hierarchygenerator', 'pyattribute', order=41)
def pyattribute(self, source, target):
    """Create Attribute.
    """
    if source.parent.stereotype('sql:sql_content') is None:
        return

    options={}

    if source.stereotype('sql:primary'):
        options['primary_key']=True
            
    targetatt = read_target_node(source, target.target)
    if options:
        oparray=[]
        for k in options:
            oparray.append('%s = %s' %(k,repr(options[k])))
        targetatt.value='Column(%s,%s)' % (source.type.name,', '.join(oparray))
    else:
        targetatt.value='Column(%s)' % source.type.name
        
#    import pdb;pdb.set_trace()
