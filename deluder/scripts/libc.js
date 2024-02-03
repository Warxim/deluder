const LIBS = module.config.libs || ["libc.so", "libsocket.so", "libpthread.so"];

/*
ssize_t send(
  int socket,
  const void *bufferPointer, 
  size_t bufferSize, 
  int flags
);

ssize_t sendto(
  int socket,
  const void *bufferPointer,
  size_t bufferSize,
  int flags,
  const struct sockaddr *dest_addr, 
  socklen_t addrlen
);

// not supported
ssize_t sendmsg(
  int socket,
  const struct msghdr *msg,
  int flags
);
*/
const createSendHandler = (func) => ({
    onEnter: function(args) {
        const socket = args[0].toInt32();
        const bufferPointer = args[1];
        this.originalDataSize = args[2].toInt32();
        const buffer = Memory.readByteArray(bufferPointer, this.originalDataSize);

        // Intercept data
        const response = interceptSend(getMetadataFromSocket(socket, 'libc'), buffer);
        
        // Create buffer for intercepted data in memory
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
});

if (module.config.send) {
  attachToFunctionInLibrariesMatching(LIBS, 'send', () => createSendHandler('send'));
}

if (module.config.sendto) {
  attachToFunctionInLibrariesMatching(LIBS, 'sendto', () => createSendHandler('sendto'));
}

/*
ssize_t recv(
  int socket, 
  void bufferPointer[.len], 
  size_t bufferSize,
  int flags
);

ssize_t recvfrom(
  int socket, 
  void bufferPointer[restrict .len],
  size_t bufferSize,
  int flags,
  struct sockaddr *_Nullable restrict src_addr,
  socklen_t *_Nullable restrict addrlen
);

// not supported
ssize_t recvmsg(
  int sockfd,
  struct msghdr *msg,
  int flags
);
*/
const createRecvHandler = (func) => ({
    onEnter: function(args) {
        this.socket = args[0].toInt32();
        this.bufferPointer = args[1];
        this.bufferSize = args[2].toInt32();
    }, 
    onLeave: function(retval) {
        const receivedDataSize = retval.toInt32();
        if (receivedDataSize <= 0) {
            return;
        }
        
        const receivedData = Memory.readByteArray(this.bufferPointer, receivedDataSize);
        
        const response = interceptRecv(getMetadataFromSocket(this.socket, 'libc'), receivedData);

        // Replace received data
        const byteLength = safeWriteToBuffer(this.bufferPointer, this.bufferSize, response.data);

        // Replace received length
        retval.replace(byteLength);
    }
});

if (module.config.recv) {
  attachToFunctionInLibrariesMatching(LIBS, 'recv', () => createRecvHandler('recv'));
}

if (module.config.recvfrom) {
  attachToFunctionInLibrariesMatching(LIBS, 'recvfrom', () => createRecvHandler('recvfrom'));
}

/*
int shutdown(
  int socket, 
  int how
);

int close(
  int socket
);
*/
const createCloseHandler = (func) => ({
  onEnter: function(args) {
      const socket = args[0].toInt32();
      processClose(getMetadataFromSocket(socket, 'libc'));
  }, 
  onLeave: function(retval) {
  }
});

if (module.config.shutdown) {
  attachToFunctionInLibrariesMatching(LIBS, 'shutdown', () => createCloseHandler('shutdown'));
}

if (module.config.close) {
  attachToFunctionInLibrariesMatching(LIBS, 'close', () => createCloseHandler('close'));
}
