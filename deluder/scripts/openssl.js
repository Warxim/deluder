const LIBS = module.config.libs || ["libssl", "openssl", "ssleay", "libeay", "libcrypto"];

const getFdFunctions = new Map();

const getFd = (lib, ssl) => {
    if (getFdFunctions.has(lib)) {
        return getFdFunctions.get(lib)(ssl);
    }
    
    const SSL_get_fd_export = Module.findExportByName(lib, 'SSL_get_fd');
    if (SSL_get_fd_export) {
        const SSL_get_fd = new NativeFunction(SSL_get_fd_export, "int", ["pointer"]);
        getFdFunctions.set(lib, SSL_get_fd);
        return SSL_get_fd(ssl);
    }
    
    const SSL_get_fd = () => null;
    getFdFunctions.set(lib, SSL_get_fd);
    return SSL_get_fd(ssl);
};

const getMetadata = (lib, ssl) => {
    const socket = getFd(lib, ssl);
    return getMetadataFromSocket(socket, 'openssl');
};

/*
int SSL_write(SSL *ssl, const void *buf, int num);
*/
if (module.config.SSL_write) {
    attachToFunctionInLibrariesMatching(LIBS, 'SSL_write', (lib) => {
        return ({
            onEnter: function(args) {
                const ssl = args[0];
                const bufferPointer = args[1];
                this.originalDataSize = args[2].toInt32();
                const buffer = Memory.readByteArray(bufferPointer, this.originalDataSize);
                
                const response = interceptSend(getMetadata(lib, ssl), buffer);
                
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
int SSL_write_ex(SSL *s, const void *buf, size_t num, size_t *written);
*/
if (module.config.SSL_write_ex) {
    attachToFunctionInLibrariesMatching(LIBS, 'SSL_write_ex', (lib) => ({
        onEnter: function(args) {
            const ssl = args[0];
            const bufferPointer = args[1];
            this.originalDataSize = args[2].toInt32();
            this.writtenPointer = args[3];
            const buffer = Memory.readByteArray(bufferPointer, this.originalDataSize);

            const response = interceptSend(getMetadata(lib, ssl), buffer);
            
            this.buffer = createBufferInMemory(response.data);

            // Set new data
            args[1] = this.buffer;

            // Replace data size
            args[2] = new NativePointer(response.data.length);
        }, 
        onLeave: function(retval) {
            this.writtenPointer.writeInt(this.originalDataSize);
        }
    }));
}

/*
int SSL_read(SSL *ssl, void *buf, int num);
*/
if (module.config.SSL_read) {
    attachToFunctionInLibrariesMatching(LIBS, 'SSL_read', (lib) => ({
        onEnter: function(args) {
            this.ssl = args[0];
            this.bufferPointer = args[1];
            this.bufferSize = args[2].toInt32();
        }, 
        onLeave: function(retval) {
            const receivedDataSize = retval.toInt32();
            if (receivedDataSize <= 0) {
                return;
            }
            const receivedData = Memory.readByteArray(this.bufferPointer, receivedDataSize);
            
            const response = interceptRecv(getMetadata(lib, this.ssl), receivedData);

            // Replace received data
            const byteLength = safeWriteToBuffer(this.bufferPointer, this.bufferSize, response.data);

            // Replace received length
            retval.replace(byteLength);
        }
    }));
}

/*
int SSL_read_ex(SSL *ssl, void *buf, size_t num, size_t *readbytes);
*/
if (module.config.SSL_read_ex) {
    attachToFunctionInLibrariesMatching(LIBS, 'SSL_read_ex', (lib) => ({
        onEnter: function(args) {
            this.ssl = args[0];
            this.bufferPointer = args[1];
            this.bufferSize = args[2].toInt32();
            this.readPointer = args[3];
        }, 
        onLeave: function(retval) {
            const resultCode = retval.toInt32();
            if (resultCode != 1) {
                return;
            }
            const receivedData = Memory.readByteArray(this.bufferPointer, this.readPointer.readInt());
            
            const response = interceptRecv(getMetadata(lib, this.ssl), receivedData);

            // Replace received data
            const byteLength = safeWriteToBuffer(this.bufferPointer, this.bufferSize, response.data);

            // Replace received length
            this.readPointer.writeInt(byteLength);
        }
    }));
}

/*
int SSL_shutdown(SSL *ssl);
*/
if (module.config.SSL_shutdown) {
    attachToFunctionInLibrariesMatching(LIBS, 'SSL_shutdown', (lib) => ({
        onEnter: function(args) {
            const ssl = args[0];
            processClose(getMetadata(lib, ssl));
        }, 
        onLeave: function(retval) {
        }
    }));
}
