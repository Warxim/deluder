//
// Messaging
//
const MessageType = {
    SEND: 's',
    RECV: 'r',
    CLOSE: 'c',
};

const MetadataType = {
    SOCKET: 's',
    PROTOCOL: 'p',
    CONNECTION_ID: 'ci',
    CONNECTION_SOURCE_IP: 'csi',
    CONNECTION_SOURCE_PORT: 'csp',
    CONNECTION_SOURCE_PATH: 'cspa',
    CONNECTION_DESTINATION_IP: 'cdi',
    CONNECTION_DESTINATION_PORT: 'cdp',
    CONNECTION_DESTINATION_PATH: 'cdpa',
    MODULE: 'm',
};

const generateMessageId = () => {
    const S4 = () => (((1+Math.random())*0x10000)|0).toString(16).substring(1);
    return (S4()+S4()+'-'+S4()+'-'+S4()+'-'+S4()+'-'+S4()+S4()+S4());
};

const intercept = (type, message, buffer) => {
    message.id = message.id ? message.id : generateMessageId();
    message.type = type;

    send(message, buffer);
    
    let responseHolder = null;

    recv(message.id, response => {
        responseHolder = response;
    }).wait();

    return responseHolder;
};

const interceptSend = (message, buffer) => intercept(MessageType.SEND, message, buffer);
const interceptRecv = (message, buffer) => intercept(MessageType.RECV, message, buffer);

const process = (type, message) => {
    message.id = message.id ? message.id : generateMessageId();
    message.type = type;

    send(message);
};

const processClose = (message) => process(MessageType.CLOSE, message);

//
// Logging
//
const log = (level, ...message) => {
    console.log(new Date().toISOString(), '[' + level + '] (Script)', ...message);
}
const logInfo = (...message) => log('INFO', ...message);
const logWarning = (...message) => log('WARN', ...message);
const logError = (...message) => log('ERROR', ...message);
const logDebug = (...message) => config.debug ? log('DEBUG', ...message) : null;

//
// Hooking
//
const MODULES = Process.enumerateModules().reduce((map, module) => {
    map[module.name.toLowerCase()] = module;
    return map;
}, {});

const attachToFunctionInLibraries = (libs, func, handlerCreator) => {
    libs.map(lib => lib.toLowerCase())
        .filter(lib => {
            if (lib in MODULES) {
                return true;
            }
            logInfo('Function', func, 'not found, since library', lib, 'is missing');
            return false;
        })
        .map(lib => ({
            name: lib,
            export: MODULES[lib].findExportByName(func)
        }))
        .filter(lib => {
            if (lib.export) {
                return true;
            }
            logInfo('Function', func, 'not found in library', lib.name);
            return false;
        })
        .forEach(lib => {
            Interceptor.attach(lib.export, handlerCreator(lib.name));
            logInfo('Hooked function', func, 'in library', lib.name);
        });
};

const attachToFunctionInLibrariesMatching = (libsNamesMatcher, func, handlerCreator) => {
    const matchingLibraries = Object.keys(MODULES)
            .filter(module => libsNamesMatcher.some(libNameMatcher => module.match(libNameMatcher)));

    if (matchingLibraries.length == 0) {
        logInfo('No matching libraries found for regexes', libsNamesMatcher);    
    }

    matchingLibraries.map(lib => ({
            name: lib,
            export: MODULES[lib].findExportByName(func)
        }))
        .filter(lib => {
            if (lib.export) {
                return true;
            }
            logInfo('Function', func, 'not found in library', lib.name);
            return false;
        })
        .forEach(lib => {
            Interceptor.attach(lib.export, handlerCreator(lib.name));
            logInfo('Hooked function', func, 'in library', lib.name);
        });
};

//
// Buffers
//
const responseDataToBuffer = (responseData) => {
    return new Uint8Array(responseData).buffer;
}

/**
 * Writes response.data to buffer safely (considering buffer size)
 * @returns Number of bytes written to the buffer
 */
const safeWriteToBuffer = (bufferPointer, bufferSize, responseData, silent) => {
    let sizedData;
    if (responseData.length > bufferSize) {
        sizedData = responseData.slice(0, bufferSize);
        if (silent !== true) {
            logInfo('Data overflows recv buffer, slicing from', responseData.length, 'to', bufferSize, 'bytes');
        }
    } else {
        sizedData = responseData;
    }
    
    const buffer = responseDataToBuffer(sizedData);
    Memory.writeByteArray(bufferPointer, buffer);

    return buffer.byteLength;
};

/**
 * Creates buffer in memory for response.data and writes the data to it
 * @returns Buffer allocated in process memory (do not forget to store it in "this", in order to keep it between onEnter and onLeave)
 */
const createBufferInMemory = (responseData) => {
    const newBuffer = responseDataToBuffer(responseData);
    const buffer = Memory.alloc(newBuffer.byteLength);
    buffer.writeByteArray(newBuffer);
    return buffer;
};

//
// Sockets
//
const getMetadataFromSocket = (socket, module) => {
    const metadata = {
        [MetadataType.SOCKET]: socket,
        [MetadataType.CONNECTION_ID]: module + '-' + socket,
        [MetadataType.MODULE]: module,
    };

    if (socket == null) {
        return metadata;
    }

    const protocol = Socket.type(socket);
    if (protocol == null) {
        return metadata;
    }

    metadata[MetadataType.PROTOCOL] = protocol;

    const localAddress = Socket.localAddress(socket);
    if (localAddress != null) {
        if (localAddress.hasOwnProperty('ip')) {
            metadata[MetadataType.CONNECTION_SOURCE_IP] = localAddress.ip;
            metadata[MetadataType.CONNECTION_SOURCE_PORT] = localAddress.port;
        } else if (localAddress.hasOwnProperty('path')) {
            metadata[MetadataType.CONNECTION_SOURCE_PATH] = localAddress.path;
        }
    }

    const peerAddress = Socket.peerAddress(socket);
    if (peerAddress != null) {
        if (peerAddress.hasOwnProperty('ip')) {
            metadata[MetadataType.CONNECTION_DESTINATION_IP] = peerAddress.ip;
            metadata[MetadataType.CONNECTION_DESTINATION_PORT] = peerAddress.port;
        } else if (peerAddress.hasOwnProperty('path')) {
            metadata[MetadataType.CONNECTION_DESTINATION_PATH] = peerAddress.path;
        }
    }
    
    return metadata;
};

const getMetadataFromCode = (code, module) => {
    return {
        [MetadataType.CONNECTION_ID]: module + '-' + code,
        [MetadataType.MODULE]: module,
    };
};

//
// Info log
//
logInfo(`Process info: id=${Process.id} architecture=${Process.arch} platform=${Process.platform}`);
