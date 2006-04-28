# Copyright 2004 Roman Yakovenko.
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# http://www.boost.org/LICENSE_1_0.txt)

"""This module contains the implementation of the L{config_t} class.
"""

class config_t(object):
    """Configuration object to collect parameters for invoking gccxml.

    This class serves as a container for the parameters that can be used
    to customize the call to gccxml.
    """
    def __init__( self
                  , gccxml_path=''
                  , working_directory='.'
                  , include_paths=None
                  , define_symbols=None
                  , undefine_symbols=None
                  , start_with_declarations=None
                  , verbose=False):
        """Constructor.
        """
        object.__init__( self )
        self.__gccxml_path = gccxml_path
        self.__working_directory = working_directory

        if not include_paths:
            include_paths = []
        self.__include_paths = include_paths

        if not define_symbols:
            define_symbols = []
        self.__define_symbols = define_symbols

        if not undefine_symbols:
            undefine_symbols = []
        self.__undefine_symbols = undefine_symbols

        if not start_with_declarations:
            start_with_declarations = []
        self.__start_with_declarations = start_with_declarations

        self.__verbose = verbose
        
    def clone(self):
        return config_t( gccxml_path=self.__gccxml_path
                         , working_directory=self.__working_directory
                         , include_paths=self.__include_paths[:]
                         , define_symbols=self.__define_symbols[:]
                         , undefine_symbols=self.__undefine_symbols[:]
                         , start_with_declarations=self.__start_with_declarations[:]
                         , verbose=self.verbose)

    def __get_gccxml_path(self):
        return self.__gccxml_path
    def __set_gccxml_path(self, new_path ):
        self.__gccxml_path = new_path
    gccxml_path = property( __get_gccxml_path, __set_gccxml_path )
    
    def __get_working_directory(self):
        return self.__working_directory
    def __set_working_directory(self, working_dir):
        self.__working_directory=working_dir
    working_directory = property( __get_working_directory, __set_working_directory )
    
    def __get_include_paths(self):
        return self.__include_paths
    include_paths = property( __get_include_paths )
    
    def __get_define_symbols(self):
        return self.__define_symbols
    define_symbols = property( __get_define_symbols )

    def __get_undefine_symbols(self):
        return self.__undefine_symbols
    undefine_symbols = property( __get_undefine_symbols )

    def __get_start_with_declarations(self):
        return self.__start_with_declarations
    start_with_declarations = property( __get_start_with_declarations )
    
    def __get_verbose(self):
        return self.__verbose
    def __set_verbose(self, val=True):
        self.__verbose = val
    verbose = property( __get_verbose, __set_verbose )