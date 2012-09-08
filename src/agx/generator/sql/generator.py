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
from node.ext.python import Import

from agx.generator.zca import utils as zcautils
from agx.generator.sql.scope import SqlContentScope, SqlTableScope, SqlSAConfigScope

registerScope('sqlcontent', 'uml2fs', [IClass] , SqlContentScope)
registerScope('sql_config', 'uml2fs', [IPackage] , SqlSAConfigScope)

def templatepath(name):
    return os.path.join(os.path.dirname(__file__), 'templates/%s' % name)

def get_pks(klass):
    '''gets the pks of an uml class'''
    res = [f for f in klass.filtereditems(IProperty) \
        if f.stereotype('sql:primary')]
    
    return res


@handler('sqlcontentclass', 'uml2fs', 'connectorgenerator',
         'sqlcontent', order=10)
def sqlcontentclass(self, source, target):
    '''sqlalchemy class'''
    targetclass = read_target_node(source, target.target)
    module = targetclass.parent
    imps = Imports(module)
    imps.set('sqlalchemy.ext.declarative', [['declarative_base', None]])
    imps.set('sqlalchemy', [['Column', None],
                           ['Integer', None],
                           ['String', None],
                           ['ForeignKey', None]])

    #find last import and do some assignments afterwards
    lastimport = [imp for imp in module.filtereditems(IImport)][-1]
    globalatts = [att for att in module.filtereditems(IAttribute)]
    classatts = [att for att in targetclass.filtereditems(IAttribute)]

    #generate the Base=declarative_base() statement
    att = Attribute(['Base'], 'declarative_base()')
    att.__name__ = 'Base'
    if not [a for a in globalatts if a.targets == ['Base']]:
        module.insertafter(att, lastimport)

    #generate the __tablename__ attribute
    if not [a for a in classatts if a.targets == ['__tablename__']]:
        tablename = Attribute(['__tablename__'], "'%s'" % (source.name.lower()))
        tablename.__name__ = '__tablename__'
        targetclass.insertfirst(tablename)

    #lets inherit from Base
    if targetclass.bases == ['object']:
        targetclass.bases = ['Base']
    else:
        if 'Base' not in targetclass.bases:
            targetclass.bases.insert(0, 'Base')

@handler('sqlcontentclass_engine_created_handler', 'uml2fs', 'connectorgenerator',
         'sqlcontent', order=11)
def sqlcontentclass_engine_created_handler(self, source, target):
    '''create and register the handler for the IEngineCreatedEvent'''
    targetclass = read_target_node(source, target.target)
    module = targetclass.parent
    imps = Imports(module)

    #check if one of the parent packages has the z3c_saconfig stereotype
    has_z3c_saconfig = False
    par = source.parent
    while par:
        if par.stereotype('sql:z3c_saconfig'):
            has_z3c_saconfig = True
        par = par.parent
    #add engine-created handler
    if has_z3c_saconfig:
        globalfuncs = [f for f in module.filtereditems(IFunction)]
        globalfuncnames = [f.functionname for f in globalfuncs]
        if 'engineCreatedHandler' not in globalfuncnames:

            imps.set('z3c.saconfig.interfaces', [['IEngineCreatedEvent', None]])
            imps.set('zope', [['component', None]])

            att = [att for att in module.filtereditems(IAttribute) if att.targets == ['Base']][0]
            ff = Function('engineCreatedHandler')
            ff.__name__ = ff.uuid #'engineCreatedHandler'
            ff.args = ('event',)
            dec = Decorator('component.adapter')
            dec.__name__ = dec.uuid
            dec.args = ('IEngineCreatedEvent',)
            ff.insertfirst(dec)
            block = Block('Base.metadata.create_all(event.engine)')
            block.__name__ = block.uuid
            ff.insertlast(block)
            module.insertafter(ff, att)

            prov = Block('component.provideHandler(engineCreatedHandler)')
            prov.__name__ = prov.uuid
            module.insertafter(prov, ff)

@handler('sqlrelations_collect', 'uml2fs', 'hierarchygenerator', 'sqlassociation')
def sqlrelations_collect(self, source, target):
    '''finds all associations, prepares them and adds them to the corrsponding classes'''
    
    detail = source.memberEnds[0]
    detailclass = detail.type
    master = source.memberEnds[1]
    masterclass = master.type

    if not masterclass.stereotype('sql:sql_content'):
        return
    if not detailclass.stereotype('sql:sql_content'):
        return

    mastertok = token(str(masterclass.uuid), True, outgoing_relations=[])
    detailtok = token(str(detailclass.uuid), True, incoming_relations=[])
    detailtok.incoming_relations.append(detail)
    mastertok.outgoing_relations.append(master)

@handler('sqlrelations_foreignkeys', 'uml2fs', 'connectorgenerator',
         'sqlcontent', order=8)
def sqlrelations_foreignkeys(self, source, target):
    '''generate foreign key attributes'''
    if not source.stereotype('sql:sql_content'):
        return

    targetclass = read_target_node(source, target.target)
    module=targetclass.parent
    #get the last attribute and append there the foreignkeys
    attrs=targetclass.attributes()
    attrnames=[att.targets[0] for att in attrs]
    lastattr = targetclass.attributes()[-1]
    incoming_relations = token(str(source.uuid), True, incoming_relations=[]).incoming_relations
    for relend in incoming_relations:
        klass=relend.parent
        otherend=relend.association.memberEnds[1]
        otherclass=otherend.type
        pks=get_pks(klass)
#        import pdb;pdb.set_trace()

        for pk in pks:
            fkname='%s_%s' % (otherend.name,pk.name)
            if fkname not in attrnames:
                attr=Attribute()
                attr.__name__=str(attr.uuid)
                targetclass.insertafter(attr,lastattr)
                attr.targets=[fkname]
                fk="ForeignKey('%s.%s')" % (otherclass.name.lower(),pk.name)
                options={}
                typename=pk.type.name
                #handle custom types (PrimitveType)
                if pk.type.stereotype('sql:sql_type'):
                    tgv=TaggedValues(pk.type)
                    typename=tgv.direct('classname','sql:sql_type',typename)
                    import_from=tgv.direct('import_from','sql:sql_type',None)
                    if import_from:
                        imps=Imports(module)
                        imps.set(import_from,[[typename,None]])
                        
                if relend.lowervalue:
                    options['nullable']='False'
                else:
                    options['nullable']='True'
                    
                oparray = []
                for k in options:
                    oparray.append('%s = %s' % (k, options[k]))
                attr.value = 'Column(%s, %s, %s)' % (typename, fk, ', '.join(oparray))

@handler('sqlrelations_relations', 'uml2fs', 'connectorgenerator',
         'sqlcontent', order=9)
def sqlrelations_relations(self, source, target):
    '''generate relations'''
    if not source.stereotype('sql:sql_content'):
        return

    targetclass = read_target_node(source, target.target)
    module=targetclass.parent
    directory=module.parent
    #get the last attribute and append there the relations
    attrs=targetclass.attributes()
    attrnames=[att.targets[0] for att in attrs]
    lastattr = targetclass.attributes()[-1]
    
    outgoing_relations = token(str(source.uuid), True, outgoing_relations=[]).outgoing_relations
    imps = Imports(module)

    if outgoing_relations:
        imps.set('sqlalchemy.orm',[['relationship',None]])
        
    for relend in outgoing_relations:
        assoc=relend.association
        klass=relend.parent
        otherend=relend.association.memberEnds[0]
        otherclass=otherend.type
        pks=get_pks(klass)
        relname=otherend.name
        tgv=TaggedValues(assoc)

        if relname not in attrnames:
            attr=Attribute()
            attr.__name__=str(attr.uuid)
            targetclass.insertafter(attr,lastattr)
            attr.targets=[relname]
            options={}
            #collect options for relationship
            if otherend.aggregationkind=='composite':
                options['cascade']="'all, delete-orphan'"
            if assoc.stereotype('sql:ordered'):
                order_by=tgv.direct('order_by', 'sql:ordered', None)
                if not order_by:
                    raise ValueError,'when setting a relation ordered you have to specify order_by!'
                #if not prefixed, lets prefix it
                if not '.' in order_by:
                    order_by='%s.%s'%(otherclass.name,order_by)
                options['order_by']="'%s'" % order_by
            if assoc.stereotype('sql:attribute_mapped'):
                keyname=tgv.direct('key', 'sql:attribute_mapped', None)
                if not keyname:
                    raise ValueError,'when defining attribute_mapped you have to specify a key'
                if assoc.stereotype('sql:ordered'):
                    # support for ordered mapped collection
                    # in this case we have to provide our own collection
                    # see http://docs.sqlalchemy.org/en/rel_0_7/orm/collections.html,
                    # secion 'Custom Dictionary-Based Collections'
                    fname = 'orderedcollection.py'
                    if fname not in directory:
                        src = JinjaTemplate()
                        src.template = templatepath(fname + '.jinja')
                        src.params = {}
                        directory[fname] = src
                        
                        #XXXso that emptymoduleremoval doesnt kick the template out
                        #better would be that jinjatemplates dont get removed at all
                        token('pymodules',True,modules=set()).modules.add(src)

                    options['collection_class']="ordered_attribute_mapped_collection('%s')" % keyname
                    imps.set('orderedcollection',[['ordered_attribute_mapped_collection',None]])
                else: #unordered
                    options['collection_class']="attribute_mapped_collection('%s')" % keyname
                    imps.set('sqlalchemy.orm.collections',[['attribute_mapped_collection',None]])

            if True or relend.navigable: #XXX .navigable isnt yet correctly parsed from uml, thus the hardcoding
                options['backref']="'%s'" % relend.name.lower()
            if assoc.stereotype('sql:lazy'):
                laziness=tgv.direct('laziness', 'sql:lazy', 'dynamic')
                options['lazy']="'%s'" % laziness

            #convert options into keyword params
            oparray = []
            for k in options:
                oparray.append('%s = %s' % (k, options[k]))
            attr.value = "relationship('%s', %s)" % (otherclass.name, ', '.join(oparray))

@handler('sqlattribute', 'uml2fs', 'hierarchygenerator', 'pyattribute', order=41)
def pyattribute(self, source, target):
    """Create Attribute.
    """
    klass=source.parent
    if not klass.stereotype('sql:sql_content'):
        return
    targetclass= read_target_node(klass, target.target)
    module=targetclass.parent

    read_target_node(source, target.target)

    typename=source.type.name
    options = {}
    if source.stereotype('sql:primary'):
        options['primary_key'] = 'True'
        
    # retrieve options if the primitive type has <<sql_type>>
    if source.type.stereotype('sql:sql_type'):
        tgv=TaggedValues(source.type)
        typename=tgv.direct('classname','sql:sql_type',typename)
        default=tgv.direct('default','sql:sql_type',None)
        if default:
            options['default']=default
        import_from=tgv.direct('import_from','sql:sql_type',None)
        if import_from:
            imps=Imports(module)
            imps.set(import_from,[[typename,None]])

    targetatt = read_target_node(source, target.target)
    if options:
        oparray = []
        for k in options:
            oparray.append('%s = %s' % (k, options[k]))
        targetatt.value = 'Column(%s,%s)' % (typename, ', '.join(oparray))
    else:
        targetatt.value = 'Column(%s)' % source.type.name


@handler('sql_config', 'uml2fs', 'hierarchygenerator', 'sql_config', order=41)
def sql_config(self, source, target):
    '''writes the sql config'''

    nsmap = {
        None: 'http://namespaces.zope.org/zope',
        'saconfig':'http://namespaces.zope.org/db',
    }

    tg = read_target_node(source, target.target)
    conf = zcautils.get_zcml(tg, 'configure.zcml', nsmap=nsmap)
    tgv = TaggedValues(source)

#    import pdb;pdb.set_trace()
    engine_name = tgv.direct('engine_name', 'sql:z3c_saconfig', 'default')
    engine_url = tgv.direct('engine_url', 'sql:z3c_saconfig', 'sqlite:///memory')
    session_name = tgv.direct('session_name', 'sql:z3c_saconfig', 'default')

    zcautils.set_zcml_directive(tg, 'configure.zcml', 'include', 'package', 'z3c.saconfig',
                                file='meta.zcml')
    zcautils.set_zcml_directive(tg, 'configure.zcml', 'saconfig:engine', 'name', engine_name, url=engine_url)
    zcautils.set_zcml_directive(tg, 'configure.zcml', 'saconfig:session', 'name', session_name, engine=engine_name)

    #write the readme
    fname = 'README-sqlalchemy.rst'
    if fname not in tg:
        readme = JinjaTemplate()
        readme.template = templatepath(fname + '.jinja')
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

