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
    IOperation,
    IClass,
    IPackage,
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
    set_copyright,
)
from node.ext.python.interfaces import (
    IClass as IPythonClass,
    IFunction,
    IAttribute,
    IImport,
)
from node.ext.python import (
    Attribute,
    Function,
    Decorator,
    Block,
)
from node.ext.zcml import (
    ZCMLNode,
    ZCMLFile,
    SimpleDirective,
    ComplexDirective,
)
from node.ext.template import JinjaTemplate

from agx.generator.zca import utils as zcautils
from agx.generator.sql.scope import SqlContentScope, SqlTableScope, SqlSAConfigScope

registerScope('sqlcontent','uml2fs',[IClass] ,SqlContentScope)
registerScope('sql_config','uml2fs',[IPackage] ,SqlSAConfigScope)

def templatepath(name):
    return os.path.join(os.path.dirname(__file__), 'templates/%s' % name)

@handler('sqlcontentclass', 'uml2fs', 'connectorgenerator',
         'sqlcontent', order=10)
def sqlcontentclass(self, source, target):
    '''sqlalchemy class'''
    targetclass = read_target_node(source, target.target)
    module=targetclass.parent
    imps=Imports(module)
    imps.set('sqlalchemy.ext.declarative',[['declarative_base',None]])
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

@handler('sqlcontentclass_engine_created_handler', 'uml2fs', 'connectorgenerator',
         'sqlcontent', order=11)
def sqlcontentclass_engine_created_handler(self, source, target):
    '''create and register the handler for the IEngineCreatedEvent'''
    targetclass = read_target_node(source, target.target)
    module=targetclass.parent
    imps=Imports(module)
    
    #check if one of the parent packages has the z3c_saconfig stereotype
#    import pdb;pdb.set_trace()
    has_z3c_saconfig=False
    par=source.parent
    while par:
        if par.stereotype('sql:z3c_saconfig'):
            has_z3c_saconfig=True
        par=par.parent
    #add engine created handler
    if has_z3c_saconfig:
        globalfuncs=[f for f in module.filtereditems(IFunction)]
        globalfuncnames=[f.functionname for f in globalfuncs]
        if 'engineCreatedHandler' not in globalfuncnames:
            
            imps.set('z3c.saconfig.interfaces',[['IEngineCreatedEvent',None]])
            imps.set('zope',[['component',None]])
            
            att=[att for att in module.filtereditems(IAttribute) if att.targets==['Base']][0]
            ff=Function('engineCreatedHandler')
            ff.__name__=ff.uuid #'engineCreatedHandler'
            ff.args=('event',)
            dec=Decorator('component.adapter')
            dec.__name__=dec.uuid
            dec.args=('IEngineCreatedEvent',)
            ff.insertfirst(dec)
            block=Block('Base.metadata.create_all(event.engine)')
            block.__name__=block.uuid
            ff.insertlast(block)
            module.insertafter(ff,att)
            
            prov=Block('component.provideHandler(engineCreatedHandler)')
            prov.__name__=prov.uuid
            module.insertafter(prov,ff)
    

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
        

@handler('sql_config', 'uml2fs', 'hierarchygenerator', 'sql_config', order=41)
def sql_config(self, source, target):
    '''writes the sql config'''
    
    nsmap = {
        None: 'http://namespaces.zope.org/zope',
        'saconfig':'http://namespaces.zope.org/db',
    }

    tg=read_target_node(source, target.target)
    conf=zcautils.get_zcml(tg,'configure.zcml',nsmap=nsmap)
    tgv=TaggedValues(source)

#    import pdb;pdb.set_trace()
    engine_name=tgv.direct('engine_name','sql:z3c_saconfig','default')
    engine_url=tgv.direct('engine_url','sql:z3c_saconfig','sqlite:///memory')
    session_name=tgv.direct('session_name','sql:z3c_saconfig','default')

    zcautils.set_zcml_directive(tg,'configure.zcml','include','package','z3c.saconfig',
                                file='meta.zcml')
    zcautils.set_zcml_directive(tg,'configure.zcml','saconfig:engine','name',engine_name,url=engine_url)
    zcautils.set_zcml_directive(tg,'configure.zcml','saconfig:session','name',session_name,engine=engine_name)

    #write the readme
    fname='README-sqlalchemy.rst'
    if fname not in tg:
        readme = JinjaTemplate()
        readme.template = templatepath(fname+'.jinja')
        readme.params = {
            'engine_name':engine_name,
            'engine_url':engine_url,
            'session_name':session_name,
            'packagename':dotted_path(source),
            }
        tg[fname] = readme

@handler('sql_dependencies', 'uml2fs', 'semanticsgenerator', 'sql_config')
def sql_dependencies(self, source, target):
    setup = target.target['setup.py']
    setup.params['setup_dependencies'].append('sqlalchemy')
    setup.params['setup_dependencies'].append('z3c.saconfig')

    