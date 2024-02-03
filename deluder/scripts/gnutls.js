const LIBS = module.config.libs || ["gnutls"];

const getFdFunctions = new Map();

const getFd = (lib, ssl) => {
    if (getFdFunctions.has(lib)) {
        return getFdFunctions.get(lib)(ssl);
    }
    
    const gnutls_transport_get_int_export = Module.findExportByName(lib, 'gnutls_transport_get_int');
    if (gnutls_transport_get_int_export) {
        const gnutls_transport_get_int = new NativeFunction(gnutls_transport_get_int_export, "int", ["pointer"]);
        getFdFunctions.set(lib, gnutls_transport_get_int);
        return gnutls_transport_get_int(ssl);
    }
    
    const gnutls_transport_get_int = () => null;
    getFdFunctions.set(lib, gnutls_transport_get_int);
    return gnutls_transport_get_int(ssl);
};

const getMetadata = (lib, session) => {
    const socket = getFd(lib, session);
    return getMetadataFromSocket(socket, 'gnutls');
};

/*
ssize_t gnutls_record_send(
    gnutls_session_t session,
    const void *bufferPointer,
    size_t bufferSize
);
*/
if (module.config.gnutls_record_send) {
    attachToFunctionInLibrariesMatching(LIBS, 'gnutls_record_send', (lib) => {
        return ({
            onEnter: function(args) {
                const session = args[0];
                const bufferPointer = args[1];
                this.originalDataSize = args[2].toInt32();
                const buffer = Memory.readByteArray(bufferPointer, this.originalDataSize);
                
                const response = interceptSend(getMetadata(lib, session), buffer);
                
                this.buffer = createBufferInMemory(response.data);

                // Set new data
                args[1] = this.buffer;

                // Replace data size
                args[2] = new NativePointer(response.data.length);
            }, 
            onLeave: function(retval) {
                // Set original size
                retval.replace(this.originalDataSize);
            }
        })
    });
}

/*
ssize_t gnutls_record_recv(
    gnutls_session_t session, 
    void * bufferPointer,
    size_t bufferSize
);
*/
if (module.config.gnutls_record_recv) {
    attachToFunctionInLibrariesMatching(LIBS, 'gnutls_record_recv', (lib) => {
        return ({
            onEnter: function(args) {
                this.session = args[0];
                this.bufferPointer = args[1];
                this.bufferSize = args[2].toInt32();
            }, 
            onLeave: function(retval) {
                const receivedDataSize = retval.toInt32();
                if (receivedDataSize <= 0) {
                    return;
                }
                
                const receivedData = Memory.readByteArray(this.bufferPointer, receivedDataSize);
                
                const response = interceptRecv(getMetadata(lib, this.session), receivedData);
        
                // Replace received data
                const byteLength = safeWriteToBuffer(this.bufferPointer, this.bufferSize, response.data);
        
                // Replace received length
                retval.replace(byteLength);
            }
        })
    });
}

/*
int gnutls_bye(
    gnutls_session_t session, 
    gnutls_close_request_t how
);
*/
if (module.config.gnutls_bye) {
    attachToFunctionInLibrariesMatching(LIBS, 'gnutls_bye', (lib) => ({
        onEnter: function(args) {
            const session = args[0];
            processClose(getMetadata(lib, session));
        }, 
        onLeave: function(retval) {
        }
    }));
}
