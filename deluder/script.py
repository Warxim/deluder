import copy
import json

from deluder.common import *
from deluder.scripts import *


def load_scripts(config: DeluderConfig) -> str:
    """
    Loads scripts using given Deluder config as a single script string
    (concatenates all scripts into single string)
    """
    source = ''
    
    source += _read_script('config')
    source += _create_config_changes(config)
    source += _read_script('common')

    for script in config.scripts:
        if script.type not in AVAILABLE_SCRIPTS:
            raise DeluderException(f'Script {script.type} not found!')
        
        script_config = copy.copy(SCRIPTS_DEFAULT_CONFIGS[script.type]) if script.type in SCRIPTS_DEFAULT_CONFIGS else dict()
        script_config.update(script.config)

        source += '\n';
        script_source = 'const module = {};';
        script_source += f'module.type = \'{script.type}\';';
        script_source += f'module.config = {json.dumps(script_config)};';
        script_source += _read_script(script.type)
        source += _wrap_script(script_source)
    
    if config.debug:
        with open('script1.js', 'w') as script_file:
            script_file.write(source)

    return source
    
def _read_script(script_name: str) -> str:
    with open(SCRIPTS_PATH + script_name + '.js', 'r') as script_file:
        return script_file.read()

def _wrap_script(script_source: str) -> str:
    return f"""
(function() {{
    {script_source}
}}());
    """

def _create_config_changes(config: DeluderConfig) -> str:
    return f"""
config.debug = {str(config.debug).lower()};    
"""
