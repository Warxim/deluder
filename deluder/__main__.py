#!/usr/bin/env python3

import argparse
import json

from deluder.core import Deluder, create_default_config
from deluder.interceptors import INTERCEPTORS_REGISTRY, AVAILABLE_INTERCEPTORS
from deluder.script import AVAILABLE_SCRIPTS, SCRIPTS_DEFAULT_CONFIGS
from deluder.common import *


def main():
    """
    Main function, which processes command-line arguments and starts Deluder core
    """
    config = create_default_config()

    def command_config():
        example_config = {
            'debug': config.debug,
            'ignoreChildProcesses': config.ignore_child_processes,
            'interceptors': [],
            'scripts': [],
        }
        for script in AVAILABLE_SCRIPTS:
            example_config['scripts'].append({
                'type': script,
                'config': dict() if script not in SCRIPTS_DEFAULT_CONFIGS else SCRIPTS_DEFAULT_CONFIGS[script],
            })
        for type, clazz in INTERCEPTORS_REGISTRY.items():
            example_config['interceptors'].append({
                'type': type,
                'config': clazz.default_config(),
            })
        print(json.dumps(example_config, indent=4))


    def list_str(values):
        return values.split(',')


    def add_common_arguments(parser: argparse.ArgumentParser):
        parser.add_argument('--remote', '-r', metavar='<host:port>',
                            help=f'Execute deluder commands on a remote host running frida-server')
        
        parser.add_argument('--debug', '-d', action='store_true', default=config.debug,
                            help='Enable debug mode with verbose output')
        
        interceptors = ','.join(AVAILABLE_INTERCEPTORS)
        parser.add_argument('--interceptors', '-i', type=list_str, metavar=interceptors,
                            help=f'Comma separated list of interceptors to use ({interceptors})')
        
        scripts = ','.join(AVAILABLE_SCRIPTS)
        parser.add_argument('--scripts', '-s', type=list_str, metavar=scripts,
                            help=f'Comma separated list of scripts to use ({scripts})')
        
        parser.add_argument('--config', '-c', metavar='config.json',
                            help=f'Set config file path, use command config in order to get example config with defaults')

        parser.add_argument('--ignore-child-processes', action='store_true', default=config.ignore_child_processes,
                            help=f'Disables automatic child process hooking')


    parser = argparse.ArgumentParser(
        prog='deluder',
        description='Deluder (https://github.com/Warxim/deluder) is an utility for hooking into networking or encryption functions of applications. '
                    'Main goal of deluder is to provide a possibility to intercept network communication of applications.'
    )

    parser.add_argument('--version', '-v', version=f'Deluder v{Deluder.version()}', action='version')
    
    # Create command parsers
    commands = parser.add_subparsers(dest='command', metavar='<command>')

    parser_run = commands.add_parser('run', help='Run new instance of application')
    add_common_arguments(parser_run)
    parser_run.add_argument('path', metavar='<args>', type=str, nargs=argparse.REMAINDER, 
                            help='Path to application and optionally application arguments')

    parser_attach = commands.add_parser('attach', help='Attach to existing instance of application')
    add_common_arguments(parser_attach)
    parser_attach.add_argument('pid_or_name', metavar='PID/ProcessName', type=str,
                            help='PID or process name of the target application')

    parser_example_config = commands.add_parser('config', help='Get example config with default values')

    # Parse arguments
    args = parser.parse_args()
    
    # Remote host
    remote_host = None

    if args.command is None:
        parser.print_help()
        exit()

    # Handle config command
    if args.command == 'config':
        command_config()
        exit()  

    # Configure
    if args.config:
        with open(args.config) as config_file:
            config_dict = json.load(config_file)

            if 'debug' in config_dict:
                config.debug = config_dict['debug']

            if 'ignoreChildProcesses' in config_dict:
                config.ignore_child_processes = config_dict['ignoreChildProcesses']
                
            if 'interceptors' in config_dict:
                config.interceptors = []
                for interceptor in config_dict['interceptors']:
                    config.interceptors.append(DeluderInterceptorConfig(type=interceptor['type'], config=interceptor['config']))
                
            if 'scripts' in config_dict:
                config.scripts = []
                for script in config_dict['scripts']:
                    config.scripts.append(DeluderScriptConfig(type=script['type'], config=script['config']))

    if args.debug:
        config.debug = True

    if args.interceptors:
        config.interceptors = []
        if args.interceptors != ['']:
            for interceptor in args.interceptors:
                config.interceptors.append(DeluderInterceptorConfig(type=interceptor, config=dict()))

    if args.scripts:
        config.scripts = []
        if args.scripts != ['']:
            for script in args.scripts:
                config.scripts.append(DeluderScriptConfig(type=script, config=dict()))

    if args.ignore_child_processes:
        config.ignore_child_processes = True

    if args.remote:
        remote_host = args.remote

    # Create deluder
    if args.command == 'run':
        deluder = Deluder.for_new_app(app_path=args.path, remote_host=remote_host, config=config)
    elif args.command == 'attach':
        if str.isdigit(args.pid_or_name):
            deluder = Deluder.for_existing_process_id(int(args.pid_or_name), remote_host=remote_host, config=config)
        else:
            deluder = Deluder.for_existing_process_name(args.pid_or_name, remote_host=remote_host, config=config)

    # Run deluder
    deluder.delude()


if __name__ == "__main__":
    main()
