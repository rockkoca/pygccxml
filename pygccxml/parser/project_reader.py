# Copyright 2004 Roman Yakovenko.
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# http://www.boost.org/LICENSE_1_0.txt)

import os
import time
import types
import source_reader 
import declarations_cache
import pygccxml.declarations
from pygccxml.utils import logger

class COMPILATION_MODE:
    ALL_AT_ONCE = 'all at once'
    FILE_BY_FILE = 'file by file'

class file_configuration_t( object ):
    class CONTENT_TYPE:
        STANDARD_SOURCE_FILE = 'standard source file'
        CACHED_SOURCE_FILE = 'cached source file'
        GCCXML_GENERATED_FILE = 'gccxml generated file'
        TEXT = 'text'
        
    def __init__( self
                  , data
                  , start_with_declarations=None
                  , content_type=CONTENT_TYPE.STANDARD_SOURCE_FILE
                  , cached_source_file=None ):
        object.__init__( self )
        self.__data = data
        if not start_with_declarations:
            start_with_declarations = []
        self.__start_with_declarations = start_with_declarations
        self.__content_type = content_type
        self.__cached_source_file = cached_source_file
        if not self.__cached_source_file \
           and self.__content_type == self.CONTENT_TYPE.CACHED_SOURCE_FILE:
            self.__cached_source_file = self.__data + '.xml'

    def __get_data(self):
        return self.__data
    data = property( __get_data )

    def __get_start_with_declarations(self):
        return self.__start_with_declarations
    start_with_declarations = property( __get_start_with_declarations )
    
    def __get_content_type(self):
        return self.__content_type
    content_type = property( __get_content_type )

    def __get_cached_source_file(self):
        return self.__cached_source_file
    cached_source_file = property( __get_cached_source_file )
    
def create_text_fc( text ):
    return file_configuration_t( data=text
                                 , content_type=file_configuration_t.CONTENT_TYPE.TEXT )

def create_source_fc( header ):
    return file_configuration_t( data=header
                                 , content_type=file_configuration_t.CONTENT_TYPE.STANDARD_SOURCE_FILE )

def create_gccxml_fc( xml_file ):
    return file_configuration_t( data=xml_file
                                 , content_type=file_configuration_t.CONTENT_TYPE.GCCXML_GENERATED_FILE )

def create_cached_source_fc( header, cached_source_file ):
    return file_configuration_t( data=header
                                 , cached_source_file=cached_source_file
                                 , content_type=file_configuration_t.CONTENT_TYPE.CACHED_SOURCE_FILE )

class project_reader_t:
    """Parses header files and returns the contained declarations.
    """
    def __init__( self, config, cache=None, decl_factory=None):
        """Constructor.

        config is a configuration object that contains the parameters
        for invoking gccxml. cache specifies the cache to use for
        caching declarations between separate runs. By default, no
        cache is used.  decl_factory is an object that must provide
        the same interface than
        L{decl_factory_t<declarations.decl_factory_t>}, i.e. there must
        be a set of C{create_*} methods that return an instance of an
        appropriate declaration class.  By default, the declaration
        classes defined in the L{declarations} package are used.

        @param config: Configuration object
        @type config: L{config_t}
        @param cache: Declaration cache (None=no cache)
        @type cache: L{cache_base_t} or str
        @param decl_factory: Custom declaration factory object or None
        @type decl_factory: decl_factory_t
        """
        self.__config = config
        self.__dcache = None
        if isinstance( cache, declarations_cache.cache_base_t ):
            self.__dcache = cache
        elif isinstance( cache, types.StringTypes ):
            self.__dcache = declarations_cache.file_cache_t(cache)
        else:
            self.__dcache = declarations_cache.dummy_cache_t()
        self.__decl_factory = decl_factory
        if not decl_factory:
            self.__decl_factory = pygccxml.declarations.decl_factory_t()
            
    def get_os_file_names( files ):
        """Returns a list of OS file names

        @param files: list of strings or L{file_configuration_t} instances. 
                      files could contain a mix of them
        @type files: list
        """
        fnames = []
        for f in files:
            if isinstance( f, types.StringTypes ):
                fnames.append( f )
            elif isinstance( f, file_configuration_t ):
                if f.content_type in ( file_configuration_t.CONTENT_TYPE.STANDARD_SOURCE_FILE
                                       , file_configuration_t.CONTENT_TYPE.CACHED_SOURCE_FILE ):
                    fnames.append( f.data )
            else:
                pass
        return fnames
    get_os_file_names = staticmethod( get_os_file_names )

    def read_files( self, files, compilation_mode=COMPILATION_MODE.FILE_BY_FILE):
        """Parse header files.

        @param files: list of strings or L{file_configuration_t} instances. 
                      files could contain a mix of them
        @type files: list
        @param compilation_mode: Determines whether the files are parsed individually or as one single chunk
        @type compilation_mode: L{COMPILATION_MODE}
        @returns: Declarations
        """
        if compilation_mode == COMPILATION_MODE.ALL_AT_ONCE \
           and len( files ) == len( self.get_os_file_names(files) ):
            return self.__parse_all_at_once(files)
        else:
            if compilation_mode == COMPILATION_MODE.ALL_AT_ONCE:
                msg = ''.join([
                    "Unable to parse files using ALL_AT_ONCE mode. " 
                    , "There is some file configuration that is not file. "
                    , "pygccxml.parser.project_reader_t switches to FILE_BY_FILE mode." ])
                logger.info( msg )
            return self.__parse_file_by_file(files)

    def __parse_file_by_file(self, files):        
        namespaces = []
        config = self.__config.clone()
        if config.verbose:
            logger.info( "Reading project files: file by file" )
        for prj_file in files:
            reader = None
            header = None
            content_type = None
            if isinstance( prj_file, file_configuration_t ):                
                del config.start_with_declarations[:]
                config.start_with_declarations.extend( prj_file.start_with_declarations )
                header = prj_file.data
                content_type = prj_file.content_type
            else:
                config = self.__config
                header = prj_file
                content_type = file_configuration_t.CONTENT_TYPE.STANDARD_SOURCE_FILE
            reader = source_reader.source_reader_t( config
                                                    , self.__dcache
                                                    , self.__decl_factory )
            decls = None
            if content_type == file_configuration_t.CONTENT_TYPE.STANDARD_SOURCE_FILE:
                decls = reader.read_file( header )
            elif content_type == file_configuration_t.CONTENT_TYPE.GCCXML_GENERATED_FILE:
                decls = reader.read_xml_file( header )
            elif content_type == file_configuration_t.CONTENT_TYPE.CACHED_SOURCE_FILE:
                #TODO: raise error when header file does not exist
                if not os.path.exists( prj_file.cached_source_file ):
                    dir_ = os.path.split( prj_file.cached_source_file )[0]
                    if dir_ and not os.path.exists( dir_ ):
                        os.makedirs( dir_ )
                    reader.create_xml_file( header, prj_file.cached_source_file )
                decls = reader.read_xml_file( prj_file.cached_source_file )
            else:
                decls = reader.read_string( header )
            namespaces.append( decls )
        if config.verbose:
            logger.info( "Flushing cache... " )
        start_time = time.clock()    
        self.__dcache.flush()
        if config.verbose:
            logger.info( "Cache has been flushed in %.1f secs" 
                          % ( time.clock() - start_time ) )
        answer = []
        if config.verbose:
            logger.info( "Joining namespaces ..." )                
        for file_nss in namespaces:
            answer = self._join_top_namespaces( answer, file_nss )
        if config.verbose:
            logger.info( "Joining declarations ..." )
        for ns in answer:
            if isinstance( ns, pygccxml.declarations.namespace_t ):
                self._join_declarations( ns )            
        leaved_classes = self._join_class_hierarchy( answer )
        types = self.__declarated_types(answer)
        if config.verbose:
            logger.info( "Relinking declared types ..." )
        self._relink_declarated_types( leaved_classes, types )
        source_reader.bind_typedefs( pygccxml.declarations.make_flatten( answer ) )
        return answer
        
    def __parse_all_at_once(self, files):
        config = self.__config.clone()
        if config.verbose:
            logger.info( "Reading project files: all at once" )
        header_content = []
        for header in files:
            if isinstance( header, file_configuration_t ):                
                del config.start_with_declarations[:]
                config.start_with_declarations.extend( header.start_with_declarations )
                header_content.append( '#include "%s" %s' % ( header.data, os.linesep ) )
            else:
                header_content.append( '#include "%s" %s' % ( header, os.linesep ) )
        return self.read_string( ''.join( header_content ) )

    def read_string(self, content):
        """Parse a string containing C/C++ source code.

        @param content: C/C++ source code.
        @type content: str
        @returns: Declarations
        """
        reader = source_reader.source_reader_t( self.__config, None, self.__decl_factory )
        return reader.read_string( content )

    def _join_top_namespaces(self, main_ns_list, other_ns_list):
        answer = main_ns_list[:]
        for other_ns in other_ns_list:
            main_ns = pygccxml.declarations.find_declaration( answer
                                                              , type=pygccxml.declarations.namespace_t
                                                              , name=other_ns.name
                                                              , recursive=False )
            if main_ns:
                main_ns.take_parenting( other_ns )
            else:
                answer.append( other_ns )
        return answer

    def _join_namespaces( self, nsref ):
        assert isinstance( nsref, pygccxml.declarations.namespace_t )
        ddhash = {} # decl.__class__ :  { decl.name : [decls] } double declaration hash
        decls = []
        for decl in nsref.declarations:
            if not ddhash.has_key( decl.__class__ ):
                ddhash[ decl.__class__ ] = { decl.name : [ decl ] }
                decls.append( decl )
            else:
                joined_decls = ddhash[ decl.__class__ ]
                if not joined_decls.has_key( decl.name ):
                    decls.append( decl )
                    joined_decls[decl.name] = [ decl ]
                else:
                    if isinstance( decl, pygccxml.declarations.calldef_t ):
                        if decl not in joined_decls[decl.name]:
                            #functions has overloading
                            decls.append( decl )
                            joined_decls[decl.name].append( decl )
                    else:
                        assert 1 == len( joined_decls[ decl.name ] )                        
                        if isinstance( decl, pygccxml.declarations.namespace_t ):
                            joined_decls[ decl.name ][0].take_parenting( decl )
        nsref.declarations = decls

    def _join_class_hierarchy( self, namespaces ):
        create_key = lambda decl:( decl.location.as_tuple()
                                   , tuple( pygccxml.declarations.declaration_path( decl ) ) )
        classes = filter( lambda decl: isinstance(decl, pygccxml.declarations.class_t )
                          , pygccxml.declarations.make_flatten( namespaces ) )
        leaved_classes = {}
        #selecting classes to leave
        for class_ in classes:
            key = create_key( class_ )
            if key not in leaved_classes:
                leaved_classes[ key ] = class_
        #replacing base and derived classes with those that should be leave
        #also this loop will add missing derived classes to the base
        for class_ in classes:
            leaved_class = leaved_classes[create_key( class_ )]
            for base_info in class_.bases:
                leaved_base = leaved_classes[ create_key( base_info.related_class ) ]
                #treating base class hierarchy of leaved_class
                leaved_base_info = pygccxml.declarations.hierarchy_info_t( 
                    related_class=leaved_base
                    , access=base_info.access )
                if leaved_base_info not in leaved_class.bases:
                    leaved_class.bases.append( leaved_base_info )
                else:
                    index = leaved_class.bases.index( leaved_base_info )
                    leaved_class.bases[index].related_class = leaved_base_info.related_class
                #treating derived class hierarchy of leaved_base
                leaved_derived_for_base_info = pygccxml.declarations.hierarchy_info_t( 
                    related_class=leaved_class
                    , access=base_info.access )
                if leaved_derived_for_base_info not in leaved_base.derived:
                    leaved_base.derived.append( leaved_derived_for_base_info )
                else:
                    index = leaved_base.derived.index( leaved_derived_for_base_info )
                    leaved_base.derived[index].related_class = leaved_derived_for_base_info.related_class
            for derived_info in class_.derived:
                leaved_derived = leaved_classes[ create_key( derived_info.related_class ) ]
                #treating derived class hierarchy of leaved_class
                leaved_derived_info = pygccxml.declarations.hierarchy_info_t( 
                    related_class=leaved_derived
                    , access=derived_info.access )
                if leaved_derived_info not in leaved_class.derived:
                    leaved_class.derived.append( leaved_derived_info )
                #treating base class hierarchy of leaved_derived
                leaved_base_for_derived_info = pygccxml.declarations.hierarchy_info_t( 
                    related_class=leaved_class
                    , access=derived_info.access )
                if leaved_base_for_derived_info not in leaved_derived.bases:
                    leaved_derived.bases.append( leaved_base_for_derived_info )
        #this loops remove instance we from parent.declarations
        for class_ in classes:
            key = create_key( class_ )
            if id( leaved_classes[key] ) == id( class_ ):
                continue
            else:
                declarations = None
                if class_.parent:
                    declarations = class_.parent.declarations
                else:
                    declarations = namespaces #yes, we are talking about global class that doesn't
                    #belong to any namespace. Usually is compiler generated top level classes
                declarations_ids = [ id(decl) for decl in declarations ]
                del declarations[ declarations_ids.index( id(class_) ) ]
        return leaved_classes

    def _relink_declarated_types(self, leaved_classes, declarated_types):
        create_key = lambda decl:( decl.location.as_tuple()
                                   , tuple( pygccxml.declarations.declaration_path( decl ) ) )
        for decl_wrapper_type in declarated_types:
            if isinstance( decl_wrapper_type.declaration, pygccxml.declarations.class_t ):
                key = create_key(decl_wrapper_type.declaration)
                if leaved_classes.has_key( key ):
                    decl_wrapper_type.declaration = leaved_classes[ create_key(decl_wrapper_type.declaration) ]
                else:
                    msg = []
                    msg.append( "Unable to find out actual class definition: '%s'." % decl_wrapper_type.declaration.name )
                    msg.append( "Class definition has been changed from one compilation to an other." )
                    msg.append( "Why did it happen to me? Here is a short list of reasons: " )
                    msg.append( "    1. There are different preprocessor definitions applied on same file during compilation" )
                    msg.append( "    2. GCC implementation details. Diamand class hierarchy will reproduce this behavior." )
                    msg.append( "       If name starts with '__vmi_class_type_info_pseudo' you can ignore this message." )
                    msg.append( "    3. Bug in pygccxml." )                    
                    logger.error( os.linesep.join(msg) )
                    #'__vmi_class_type_info_pseudo1' 
                

    def _join_declarations( self, declref ):
        self._join_namespaces( declref )
        for ns in declref.declarations:
            if isinstance( ns, pygccxml.declarations.namespace_t ):
                self._join_declarations( ns )
        
    def __declarated_types(self, namespaces):
        def get_from_type(cpptype):
            if not cpptype:
                return []
            elif isinstance( cpptype, pygccxml.declarations.fundamental_t ):
                return []
            elif isinstance( cpptype, pygccxml.declarations.declarated_t ):
                return [ cpptype ]
            elif isinstance( cpptype, pygccxml.declarations.compound_t ):
                return get_from_type( cpptype.base )
            elif isinstance( cpptype, pygccxml.declarations.calldef_type_t ):
                types = get_from_type( cpptype.return_type )
                for arg in cpptype.arguments_types:
                    types.extend( get_from_type( arg ) )
                return types
            else: 
                assert isinstance( cpptype, pygccxml.declarations.unknown_t )
                return []
        types = []
        for decl in pygccxml.declarations.make_flatten( namespaces ):
            if isinstance( decl, pygccxml.declarations.calldef_t ):
                types.extend( get_from_type( decl.function_type() ) )
            elif isinstance( decl, (pygccxml.declarations.typedef_t, pygccxml.declarations.variable_t) ):
                types.extend( get_from_type( decl.type ) )
        return types