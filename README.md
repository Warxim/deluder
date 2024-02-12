# Deluder
[![Release](https://img.shields.io/github/release/Warxim/deluder?labelColor=383b53&color=737dde)](https://github.com/Warxim/deluder/releases)
[![License: GPL v3](https://img.shields.io/github/license/Warxim/petep?labelColor=383b53&color=98a0e3)](https://www.gnu.org/licenses/gpl-3.0)
![python: 3.9](https://img.shields.io/badge/python-3.9-0?labelColor=383b53&color=737dde)

Deluder is a tool for intercepting traffic of proxy unaware applications. 
It is based on [Frida](https://frida.re/) and uses dynamic instrumentation to intercept communication in common networking libraries on multiple platforms. 

Deluder was primarily designed to work with [PETEP (PEnetration TEsting Proxy)](https://github.com/Warxim/petep), 
but can also be used as a standalone utility for traffic interception.

Video: [Youtube Deluder & PETEP](https://www.youtube.com/watch?v=mDcOBM8cu2g)

## Networking Libraries
Since Deluder is based on dynamic instrumentation, there is a need for custom scripts
for each networking library (e.g. Winsock, OpenSSL, GnuTLS).

Currently, Deluder support the following libraries out of the box:
- WinSock (ws2_32.dll, wsock32.dll)
  - send
  - sendto
  - recv
  - recvfrom
  - WSA_Send
  - WSA_SendTo
  - WSA_Recv
  - WSA_RecvFrom
- Linux sockets (libc.so)
  - send
  - sendto
  - recv
  - recvfrom
- OpenSSL (libssl.dll, ssleay.dll, libssl.dylib)
  - SSL_write
  - SSL_write_ex
  - SSL_read
  - SSL_read_ex
- GnuTLS (libgnutls.so, libgnutls.dll, libgnutls.dylib)
  - gnutls_record_send
  - gnutls_record_recv
- SChannel (Secur32.dll)
  - EncryptMessage
  - DecryptMessage

Scripts for each library are written in JavaScript and can be easily modified or added in
[deluder/scripts](deluder/scripts).

***Note:** Main purpose of Deluder is to support networking/encryption libraries, 
but you can eventually write scripts to intercept any library functions.*

## Installation & Usage
**Requirements:** Python 3.9+

### Installation
Deluder is a built on Python and gives you two options, how to use it:
1. Install it as CLI command using setuptools
   - [Download latest Deluder release](https://github.com/Warxim/deluder/releases/latest)
   or clone the repo `git clone https://github.com/Warxim/deluder.git`
   - Install Deluder using setuptools
       ```shell
       python setup.py install
       ```
   - Run Deluder as a command
       ```shell
       deluder --help
       ```
2. Install requirements and use it in development mode (supports adding new interceptors and scripts without the need for reinstalling)
   - [Download latest Deluder release](https://github.com/Warxim/deluder/releases/latest)
      or clone the repo `git clone https://github.com/Warxim/deluder.git`
   - In downloaded deluder directory, run installation of requirements
       ```shell
       python -m pip install -r requirements.txt
       ```
   - Run Deluder as module
       ```shell
       python -m deluder --help
       ```

### Usage
There are three main commands in deluder:
- **config** - displays default configuration file structure in JSON
- **run [app]** - runs new process and attaches Deluder to it
- **attach [pid/process name]** - attaches to process by PID or process name

Example usages:
```shell
# Display help
deluder --help
deluder run --help
deluder attach --help

# Display default config
deluder config

# Run process and attach to it
deluder run -c config.json "C:/Application.exe"
deluder run -i petep "C:/Application.exe"
deluder run --debug --interceptors log,proxifier,log --scripts schannel,openssl "C:/Application.exe"

# Attach to existing process
deluder attach -c config.json 12501
deluder attach -i petep 12501
deluder attach -s schannel,openssl -i log 12000
deluder attach -c config.json "Application.exe"

# Run process and attach to it in a remote host (10.0.0.1 on port 27042) 
deluder run -r 10.0.0.1:27042 -c config.json "C:/Application.exe"
deluder run -r 10.0.0.1:27042 -i petep "C:/Application.exe"
deluder run --remote 10.0.0.1:27042 --debug --interceptors log,proxifier,log --scripts schannel,openssl "C:/Application.exe"

# Attach to existing process in a remote host (10.0.0.1 on port 27042) 
deluder attach -r 10.0.0.1:27042 -c config.json 12501
deluder attach -r 10.0.0.1:27042 -i petep 12501
deluder attach -r 10.0.0.1:27042 -s schannel,openssl -i log 12000
deluder attach -r 10.0.0.1:27042 -c config.json "Application.exe"
```

Both attach and run have the following parameters:
- **-c/--config [path-to-config.json]** - Uses given config (recommended)
- **-d/--debug** - Enables debug with verbose output
- **-i/--interceptors [proxifier,log,log]** - Enables given interceptors
- **-s/--scripts [winsock,openssl]** - Enables given scripts (networking libraries)
- **-r/--remote [ip:port]** - Uses remote frida-server host
- **--ignore-child-processes** - Disables automatic child process hooking

#### Recommended Usage
It is recommended to first store config template to a file:
```shell
deluder config > config.json
```

and then configure the deluder through the config.json:
- setup interceptors
  - depending on your needs, you can add/remove interceptors
  - if you use Deluder with PETEP, simply remove all interceptors except for "petep" from the config file
- setup scripts
  - If you are testing an application, you should only enable scripts for used libraries.
  - If you do not know, which scripts to use, usually it is good to start first with
    the SSL/TLS libraries (openssl, schannel, gnutls) and if these are not capturing anything, 
    try to use socket libraries (winsock, libc). 

and then run the deluder through attach or run commands:
```shell
deluder run -c config.json "C:/Application.exe"
deluder attach -c config.json 12501
deluder attach -c config.json "Application.exe"
```

## PETEP
In order to use Deluder with graphical interface, you can use [PETEP (PEnetration TEsting Proxy)](https://github.com/Warxim/petep),
which supports integration with Deluder and allows you to conveniently work with the intercepted data.

![PETEP](https://petep.warxim.com/img/social/deluder.png)

In PETEP you can simply add Deluder proxy or use Deluder preset, which already has Deluder proxy configured. After that you can run Deluder using the following commands:

```shell
deluder run -i petep "C:/Application.exe"
deluder attach -i petep 12501
deluder attach -i petep "Application.exe"
```

Deluder will use a special protocol in order to intercept the data in PETEP.
 (By default, port 8008 will be used as PETEP server port for Deluder integration.)

Example minimal config for Deluder and PETEP integration:
```json
{
    "ignoreChildProcesses": false,
    "interceptors": [
        {
            "type": "petep",
            "config": {
                "petepHost": "127.0.0.1",
                "petepPort": 8008,
                "autoCloseConnections": true,
                "multipleConnections": true
            }
        }
    ],
    "scripts": [
        {
            "type": "winsock",
            "config": {}
        },
        {
            "type": "openssl",
            "config": {}
        },
        {
            "type": "gnutls",
            "config": {}
        },
        {
            "type": "libc",
            "config": {}
        },
        {
            "type": "schannel",
            "config": {}
        }
    ]
}
```
*Note: Do not try to drop intercepted messages, since that is not supported and will break the interception.*

## Proxifier
If you do not want to use PETEP, you can use any other proxy tool and use Proxifier interceptor to tunnel the intercepted data through the proxy.

Before running Deluder, setup the proxy tool, so that the proxy server is running.
After that you can run Deluder and attach it to some process.

*Note: Do not try to drop intercepted messages, since that is not supported and will break the interception.*

### Setting up Deluder for Proxifier
You can choose two types of proxifying strategies:
- **length** (default) - relies on 4B length sent before the intercepted data (`[4B data length][data]`)
- **suffix** - relies on appending contant suffix to intercepted data
- **buffer** - relies on buffer size and requires you to setup big enough buffer in both proxy tool and Deluder

## Interceptor Modules
In order to write custom interceptor modules, you can add new file with the module
in [deluder/interceptors](deluder/interceptors) and register the module by adding it to
`INTERCEPTORS_REGISTRY` in [deluder/interceptors/\_\_init\_\_.py](deluder/interceptors/__init__.py).

Each interceptor module has important methods:
- `default_config()`
    - provides default config, which can be overriden through command arguments
- `init()`
    - when interceptor gets initialized 
- `intercept(message)`
    - intercept message
- `destroy()`
    - called when Deluder finishes

The most important method for you will be the `intercept` method, in which you 
can process the traffic. The message parameter is mutable and you can modify the data inside.

## Remote Host 
In order to intercept network communication of applications on remote hosts, on which you cannot run the deluder and PETEP itself, 
you can use Frida server, to which you can connect from Deluder.

See [Frida Releases](https://github.com/frida/frida/releases) and download frida-server for your platform. Once you run the frida-server, you can use Deluder's `-r` parameter to execute the attach/run commands on the remote machine. 

For example, on remote machine, you can run:
```shell
frida-server -l 0.0.0.0:27042
```
and then run the following on your local machine:
```shell
deluder run -r REMOTE_IP:27042 -i log "C:/Application.exe"
```

## Script Modules

In order to write custom script modules for networking libraries, you can simply
create a new js files in [deluder/scripts](deluder/scripts) and then add them 
to the config file or `-s/--scripts` parameter.

It is recommended to check existing scripts and use them as inspiration.
For more information on how to write these scripts, 
you can check official [Frida guide](https://frida.re/docs/javascript-api/).

### Common functions
All scripts can use common functions, which are available in the `common.js` file,
which is automatically loaded before the custom scripts. 

### Module variables
Each module has two own variables:
- `module.type` - module code (file name without extension)
- `module.config` - module config provided in Deluder config file

## Deluder vs EchoMirage
Deluder uses similar approach known from EchoMirage to intercept the traffic of applications, 
but thanks to Frida library, it also supports other platforms than Windows.
Currently Deluder supports a few extra libraries in comparison to EchoMirage and it is possible 
to extend Deluder with more protocols for multiple platforms (like Windows, Linux, Mac).

## License
Deluder is licensed under GNU GPL 3.0.
