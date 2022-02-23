#import torch
from typing import Union, List, Type, Any, Tuple, Optional, NamedTuple, Callable, Dict

import inspect
import ast
from textwrap import dedent
#from torch._C import ErrorReport
import functools
import re
import warnings
REGEX_SUPER_CALL = re.compile(r"super\(.*\)\.__init__\(.*\)")
REGEX_GET_SUPER_ARGS = re.compile(r"super\(.*\)\.__init__\((.*)\)")
REGEX_DUNDER_INIT_ARGS = re.compile(r"def\s+__init__\((.*)\)\s*.*:")

REGEX_FUNCTION_ARGS = re.compile(r"def\s+[^\(]+\((.+)\)")
REGEX_FUNCTION_DEF = re.compile(r"(def\s+[^\(]+\(.*\).*:)")

#                  Dict[python_class_type] -> ( Dict[(init_type_definitions)] -> Tuple[jitted_class, class_string_repr_python]
GLOBAL_CLASS_DICT: Dict[Type, Dict[Tuple[Any,...], Tuple[Any, str]]] = dict()

import string
import random

# TODO: ensure uniqueness rather than just like... what are the odds y'know
def id_generator(size=15, chars=string.ascii_uppercase + string.ascii_lowercase):
    return ''.join(random.choice(chars) for _ in range(size))

class NO_DEFAULT:
    pass


'''
def inline_super(func: Callable):
    FUNCTION_DEF_REGEX = re.compile(r"def\s+__init__\(.+\).*:\s*\n")
    source = inspect.getsource(func)
    dedent_source = dedent(source)
    function_header = re.findall(FUNCTION_DEF_REGEX, dedent_source)[0]
    function_body = re.sub(FUNCTION_DEF_REGEX, "", dedent_source)

    def helper(func: str):
        #print(function_body)
        init_callname_regex = re.compile(r".+\.__init__")

        init_calls_in_source: List[str] = re.findall(init_callname_regex, func)

        # No super calls, just return source
        if len(init_calls_in_source) == 0:
            return func

        assert len(init_calls_in_source) == 1, "No, no, no, not doing multiple inheritance"
        # call to super function
        super_call: str = init_calls_in_source[0]
        # actual code in super function
        super_call_code: str = dedent(inspect.getsource(eval(super_call)))
        super_call_code = re.sub(FUNCTION_DEF_REGEX, "", super_call_code) # remove function definition
        # replace call to super with inlined code
        # step 1: get line of code to replace
        full_super_call_init_regex = re.compile(r".+\.__init__\(.+\)\s*\n") # pattern to pull

        inlined_source = re.sub(full_super_call_init_regex, super_call_code, func)
        #breakpoint()
        return helper(inlined_source)
    
    return function_header + helper(function_body)




'''

def get_function_body(func: str) -> str:
    """
    Expect:
    def dummy(*args, **kwargs):
        body
    returns: body
    """
    function_definitions = re.findall(REGEX_FUNCTION_DEF, func)
    if len(function_definitions) != 1:
        raise ValueError(f"get_function_body does not support nested functions! given {func}")
    string = re.sub(REGEX_FUNCTION_DEF, "", func)
    return string


def get_function_parameters(func: str) -> Tuple[Dict[str, str], Dict[str, Tuple[str, str]]]:
    """
    Expects:
    def dummy(*args, **kwargs):
        ...
    returns: dict[*args] = types, dict[*kwargs] = (types, defaults)
    """
    parameters = re.findall(REGEX_FUNCTION_ARGS, func)
    if len(parameters) != 1:
        raise ValueError(f"get_function_arguments does not support nested functions: passed func {func}")
    parameters: str = parameters[0]
    split_params = parameters.split(",")

    arg_to_type: Dict[str, str] = dict()
    kwargs_to_default_and_type: Dict[str, Tuple[str, str]] = dict()
    for param in split_params:
        if "=" in param: #kwarg stuff
            arg_and_type, default = param.split("=")
            if ":" in arg_and_type:
                arg, type_hint = arg_and_type.split()
                kwargs_to_default_and_type[arg.strip()] = (type_hint, default)
            else:
                kwargs_to_default_and_type[arg_and_type] = (None, default)

        else:
            if ":" in param:
                arg, type_hint = param.split(":")
                arg_to_type[arg.strip()] = type_hint.strip()
            else:
                arg_to_type[param.strip()] = None
    
    return arg_to_type, kwargs_to_default_and_type

def get_super_call(_init_method: str) -> str:
    super_call = re.findall(REGEX_SUPER_CALL, _init_method)
    if len(super_call) != 1:
            raise ValueError(f"Error passed init {_init_method} made multiple calls to super!")
    return super_call[0]

def get_super_passed_args_and_kwargs(super_call: str) -> Tuple[Tuple[str,...],  Tuple[Tuple[str, str], ...]]:
    """
    Expects: super(self, Type).__init__(*args, **kwargs) || super().__init__(*args, **kwargs)
    Returns: (arg1, arg2, ..), ( (kwarg1, default1), (kwarg2, default2)....)
    """
    passed_args = re.findall(REGEX_GET_SUPER_ARGS, super_call)
    if len(passed_args) != 1:
        raise ValueError(f"get_super_passed_args_and_kwargs: expects super().__init__, recieved {super_call}")
    passed_args: str = passed_args[0]
    split_args = passed_args.split(",")
    args: List[str] = list()
    kwargs: List[Tuple[str, str]] = list()
    for arg in split_args:
        if "=" in arg: #iskwarg
            # do kwarg stuff
            split_kwarg = arg.split("=")
            if len(split_kwarg) != 2:
                raise ValueError(f"get_super_passed_args_and_kwargs split kwarg failure {arg}")
            kwargs.append((split_kwarg[0].strip(), split_kwarg[1].strip()))
        else:
            args.append(arg.strip())
    
    return tuple(args), tuple(kwargs)




def get_tabbing(function_source: str) -> str:
    """
    Param: function_body: the body of a function isolated from inspect.getsource
    Returns: a string representing the tabbing for all inserted new code
    Expects spaces, you have to be extra retarded
    I.E 
    class NameSpace:
        def function():
            body
    if passed function would return
    '       '
    """
    
    #return " "*(inspect.indentsize(function_source))
    
    raise RuntimeError("Not implemented fuck me please I hope I never have to implement this")



def push_inherited_methods(sub_class_type: Type, super_class_type: Type, new_class_string: str) -> str:
    """
    class Base:
        ...
    class SubClass(Base):
        ...
    Expects: (SubClass, Base, string)
    where string is the running class we are recreating that can be passed to torchscript
    Returns: updated new_class_string
    """
    base_methods = set(vars(super_class_type).keys()) - set(vars(sub_class_type).keys()) # this is loose could use improved implementation
    #breakpoint()
    base_methods = list(filter(lambda method: not method.startswith("__"), base_methods)) # yes this is jank
    vars_base = vars(super_class_type)
    base_class_indentation = inspect.indentsize(new_class_string)
    for method_name in base_methods:
        method = vars_base[method_name]
        method_source = inspect.getsource(method).strip() + "\n" # I still want the \n, prolly a less stupid way of doing this
        new_class_string += "\n"+(base_class_indentation+4)*" " + method_source
        #breakpoint()
        
    return new_class_string




def inline_class(_class: Type):
    parents = _class.__mro__[1:-1]
    if len(parents) == 0:
        raise ValueError("Provided class inherits jack shit")
    first_parent = parents[0] # only dealing with you for now
    #init_source: Optional[str] = None

    init_source = inspect.getsource(_class.__init__)
    super_source = inspect.getsource(first_parent.__init__)
    super_call = get_super_call(init_source)

    super_passed_args, super_passed_kwargs  = get_super_passed_args_and_kwargs(super_call)
    super_def_args, super_def_kwargs = get_function_parameters(super_source)
    cp = super_source
    # replace super code with passed_args
    super_body = get_function_body(super_source)

    del super_def_args["self"] # ya know shouldn't be there lel
    if len(super_passed_args) != len(super_def_args):
        raise ValueError(f"Super expected {len(super_def_args)} args, recieved {len(super_passed_args)} ")

    # replace passed args
    for passed_arg, (def_arg, def_type) in zip(super_passed_args, super_def_args.items()):
        # Should do some type check stuff prolly
        super_body = super_body.replace(def_arg, passed_arg)
    

    # replace pass kwargs
    for (passed_kwarg_name, passed_kwarg_value), (def_kwarg, (def_type, def_default)) in zip(super_passed_kwargs, super_def_kwargs.items()):
        super_body = super_body.replace(def_kwarg, passed_kwarg_name)

    # replace non replaced default kwargs with their default values
    define_kwargs = []
    for def_kwarg, (def_type, def_default) in super_def_kwargs.items():
        define_kwargs.append(f"{def_kwarg.strip()} {def_type} = {def_default}\n")
    
    kwargs_def_string = ''.join(define_kwargs)
    super_body = kwargs_def_string + super_body


    old_super_body = get_function_body(super_source)
    new_init_source = init_source.replace(super_call, super_body)
    
    class_source = inspect.getsource(_class)
    new_class_source = class_source.replace(init_source, new_init_source)



    # -------- copy methods defined in super_class -------
    new_class_source = push_inherited_methods(_class, first_parent, new_class_source)

    # replace class name
    new_name = id_generator()
    new_class_source = re.sub(f"class\s+{_class.__name__}", f"class {new_name}", new_class_source)
    return new_class_source


def get_passed_args(call_string: str):
    passed_args = re.findall(REGEX_GET_SUPER_ARGS, call_string)
    #regex_passed_args = re.compile(r".+\((.*)\)")
    #passed_args = re.findall(regex_passed_args, call_string)
    if len(passed_args) != 1:
        raise ValueError(f"Passed args expects one call.. fname(arg1, arg2,..kwargs...), got {call_string}")
    passed_args: str = passed_args[0]
    split_args = passed_args.split(",")
    arg_to_kwarg_specifier: List[str] = []
    for arg in split_args:
        if "=" not in arg:
            arg_to_kwarg_specifier.append((None, arg))
        else:
            split_arg = arg.strip().split("=")
            if len(split_arg) != 2:
                raise RuntimeError(f"Literally how are you passing variables {arg} in {call_string}")
            arg_to_kwarg_specifier.append((split_arg[0].strip(), split_arg[1].strip()))
    return arg_to_kwarg_specifier

def pull_function_parameters(func: Union[Callable, str]):
    if type(func) != str:
        source = inspect.getsource(func)
    else:
        source = func
    regex_function_definition = re.compile(r"def\s+.+\((.*)\)")
    args: List[str] = re.findall(regex_function_definition, source)
    if len(args) != 1:
        raise RuntimeError(f"pull_function_parameters def failure, does not handle nested class declarations {source}")

    args: str = args[0]
    split_args = args.split(",")
    param_name_to_default = list()
    for arg in split_args:
        if arg == "self":
            continue
        if "=" not in arg:
            param_name_to_default.append((arg.strip(), NO_DEFAULT))
        else:
            split_arg = arg.strip().split("=")
            if len(split_arg) != 2:
                raise RuntimeError(f"Honestly I don't know man, why does ur default parameters ahve multiple =, {arg} in {func}")
            param_name_to_default.append((split_arg[0].strip(), split_arg[1].strip()))
    return param_name_to_default


def Inherit(classType):
    def decorator(*args):
        #print(classType)
        #print(args)
        # Modify init method
        parent = classType.__mro__[1]
        if parent == object:
            raise ValueError(f"Passed class: {classType} does not inherit anything")
        
        init_source = inspect.getsource(classType.__init__)
        super_call = re.findall(REGEX_SUPER_CALL, init_source)
        if len(super_call) != 1:
            raise ValueError(f"Passed class {classType} either calls super multiple times or never: source {init_source}")
        super_call = super_call[0]
        

        super_source = inspect.getsource(parent.__init__)
        #super_init_parameters = inspect.signature(parent.__init__)#re.findall(REGEX_DUNDER_INIT_ARGS,)
        super_init_parameters = pull_function_parameters(parent.__init__)
        #super_passed_args = get_passed_args()
        passed_args = get_passed_args(super_call)

        # in line function body
        super_source_body = re.sub(REGEX_DUNDER_INIT_ARGS, "", super_source)
        cp = super_source_body
        
        # kwargs must be internally defined
        kwarg_params = '\n'.join(map(lambda x: f"{x[0]} = {x[1]}", filter(lambda x: x[1] is not NO_DEFAULT,super_init_parameters)))
        
        #super_source_body = kwarg_params + super_source_body


        for (kwarg_specifier_passed, passed), (arg_specifier_param, default) in zip(passed_args, super_init_parameters):
            #print(passed, arg_specifier_param, arg_specifier_param=="r3")
            if kwarg_specifier_passed is not None:
                super_source_body = super_source_body.replace(kwarg_specifier_passed, passed)

            super_source_body = super_source_body.replace(arg_specifier_param, passed)

        breakpoint()

        #print(inspect.getsource(classType.__init__))
        

        return classType(args)
    return decorator




class superstr:
    pass
class supertuple:
    pass
class superint:
    pass

class One:
    def __init__(self, random_input: superstr, r2: supertuple, r3: superint, kwargs: Optional[Any]=None):
        self.oneVar = 1
        self.common = 10
        r = r2*r3
        x = random_input**2
        some_var = kwargs
    def one_method(self):
        print("One method")
    
    def overloaded(self):
        pass

classDeclaration = """
class FromString:
    def __init__(self):
        print('FromStringCreated')
        self.var = 10
"""




exec(classDeclaration)

#import torch


#@Inherit
class Two(One):
    def __init__(self, TWO_INIT1: str, TWO_INIT2: Tuple, TWO_INIT3: int, TWO_INIT_KWARG: Optional[Any] =None):
        # my comment
        super().__init__(TWO_INIT1, TWO_INIT2, TWO_INIT3, kwargs = "test")
        self.twoVar = 2

    def two_method(self):
        print("Some bullshit")

    def overloaded(self):
        print("now i do stuff")
#GLOBAL_DICT = dict() # key = tuple(type signautes), (tuple(int, int, double) -> compiled class)


def factory(*args):
    # iterates over the passed arguments, checks there types
    # t = Two() -> t = Two.__init__()
    # t = Two() -> check to see if Two with arg signature compiled -> if yes -> go to it -> if not create class with type signature, compile and return it

    pass



if __name__ == "__main__":
    #tmp = inline_super(Two.__init__)
    #twoInit = parse_def(Two.__init__)
    #t = Two(5)
    #print(t.twoVar)
    inline_class(Two)