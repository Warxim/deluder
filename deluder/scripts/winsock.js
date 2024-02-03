const LIBS = module.config.libs || ["ws2_32.dll", "wsock32.dll"];

//
// Basic Winsock API
//
/*
int WSAAPI send(
  [in] SOCKET     socket,
  [in] const char *bufferPointer,
  [in] int        dataSize,
  [in] int        flags
);

int WSAAPI sendto(
  [in]  SOCKET        socket,
  [out] char          *bufferPointer,
  [in]  int           bufferSize,
  [in]  int           flags,
  [in] const sockaddr *to,
  [in] int            tolen
);
*/
const createSendHandler = (func) => ({
    onEnter: function(args) {
        const socket = args[0].toInt32();
        const bufferPointer = args[1];
        this.originalDataSize = args[2].toInt32();
        const buffer = Memory.readByteArray(bufferPointer, this.originalDataSize);

        // Intercept data
        const response = interceptSend(getMetadataFromSocket(socket, 'wsock'), buffer);
        
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
  attachToFunctionInLibraries(LIBS, 'send', () => createSendHandler('send'));
}

if (module.config.sendto) {
  attachToFunctionInLibraries(LIBS, 'sendto', () => createSendHandler('sendto'));
}

/*
int recv(
  [in]  SOCKET socket,
  [out] char   *bufferPointer,
  [in]  int    bufferSize,
  [in]  int    flags
);

int recvfrom(
  [in]                SOCKET   socket,
  [out]               char     *bufferPointer,
  [in]                int      bufferSize,
  [in]                int      flags
  [out]               sockaddr *from,
  [in, out, optional] int      *fromlen
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
        
        const response = interceptRecv(getMetadataFromSocket(this.socket, 'wsock'), receivedData);

        // Replace received data
        const byteLength = safeWriteToBuffer(this.bufferPointer, this.bufferSize, response.data);

        // Replace received length
        retval.replace(byteLength);
    }
});

if (module.config.recv) {
  attachToFunctionInLibraries(LIBS, 'recv', () => createRecvHandler('recv'));
}

if (module.config.recvfrom) {
  attachToFunctionInLibraries(LIBS, 'recvfrom', () => createRecvHandler('recvfrom'));
}

//
// WSA Winsock API
//
const forEachWsaBuf = (buffersPointer, buffersCount, handler) => {
  let buffer = buffersPointer;
  for (let i = 0; i < buffersCount; ++i) {
      handler(buffer);
      
      // Move to next buffer (4B len, on x64 +4B alignment padding, pointer)
      buffer = buffer.add(Process.pointerSize * 2);
  }
};

/*
int WSAAPI WSASend(
[in]  SOCKET                             socket,
[in]  LPWSABUF                           buffers,
[in]  DWORD                              buffersCount,
[out] LPDWORD                            sentBytesPointer,
[in]  DWORD                              dwFlags,
[in]  LPWSAOVERLAPPED                    lpOverlapped,
[in]  LPWSAOVERLAPPED_COMPLETION_ROUTINE lpCompletionRoutine
);

int WSAAPI WSASendTo(
[in]  SOCKET                             socket,
[in]  LPWSABUF                           buffers,
[in]  DWORD                              buffersCount,
[out] LPDWORD                            sentBytesPointer,
[in]  DWORD                              dwFlags,
[in]  const sockaddr                     *lpTo,
[in]  int                                iTolen,
[in]  LPWSAOVERLAPPED                    lpOverlapped,
[in]  LPWSAOVERLAPPED_COMPLETION_ROUTINE lpCompletionRoutine
);

typedef struct _WSABUF {
ULONG len;
CHAR  *buf;
} WSABUF, *LPWSABUF;
*/
const createWSASendHandler = (func) => ({
  onEnter: function(args) {
      const socket = args[0].toInt32();
      const buffers = args[1];
      const buffersCount = args[2].toInt32();
      this.sentBytesPointer = args[3];

      if (buffersCount <= 0) {
          return;
      }

      this.buffersInMemory = [];
      this.previousLength = 0;
      forEachWsaBuf(buffers, buffersCount, (buffer) => {
          const bufferSize = buffer.readULong();
          const bufferPointer = buffer.add(Process.pointerSize).readPointer(); // 4B ULONG (on x64 +4B alignment)
          const data = Memory.readByteArray(bufferPointer, bufferSize);
          this.previousLength += bufferSize;
  
          // Intercept the data
          const response = interceptSend(getMetadataFromSocket(socket, 'wsock'), data);
          
          // Create buffer for intercepted data in memory (and store it, so it is not cleared before the function finishes)
          const newBuffer = createBufferInMemory(response.data);
          this.buffersInMemory.push(newBuffer);
          
          // Replace length and buffer pointer
          buffer.writeULong(response.data.length);
          buffer.add(Process.pointerSize).writePointer(newBuffer);
      });
  },
  onLeave: function(retval) {
      if (retval.toInt32() != 0) {
          return;
      }

      // Set bytes sent to the expected value
      if (!this.sentBytesPointer.isNull()) {
          this.sentBytesPointer.writeInt(this.previousLength);
      }
  }
});

if (module.config.WSASend) {
  attachToFunctionInLibraries(LIBS, 'WSASend', () => createWSASendHandler('WSASend'));
}

if (module.config.WSASendTo) {
  attachToFunctionInLibraries(LIBS, 'WSASendTo', () => createWSASendHandler('WSASendTo'));
}

/*
int WSAAPI WSARecv(
[in]      SOCKET                             socket,
[in, out] LPWSABUF                           buffers,
[in]      DWORD                              buffersCount,
[out]     LPDWORD                            receivedBytesPointer,
[in, out] LPDWORD                            flags,
[in]      LPWSAOVERLAPPED                    overlapped,
[in]      LPWSAOVERLAPPED_COMPLETION_ROUTINE completionRoutine
);

int WSAAPI WSARecvFrom(
[in]      SOCKET                             socket,
[in, out] LPWSABUF                           buffers,
[in]      DWORD                              buffersCount,
[out]     LPDWORD                            receivedBytesPointer,
[in, out] LPDWORD                            flags,
[out]     sockaddr                           *lpFrom,
[in, out] LPINT                              lpFromlen,
[in]      LPWSAOVERLAPPED                    overlapped,
[in]      LPWSAOVERLAPPED_COMPLETION_ROUTINE completionRoutine
);
*/
const createWSARecvHandler = (func) => ({
  onEnter: function(args) {
      this.socket = args[0].toInt32();
      this.buffers = args[1];
      this.buffersCount = args[2].toInt32();
      this.receivedBytesPointer = args[3];
      this.flags = args[4];
      if (func === 'WSARecv') {
          this.overlapped = args[5];
          this.completionRoutine = args[6];
      } else if (func === 'WSARecvFrom') {
          this.overlapped = args[7];
          this.completionRoutine = args[8];
      }
  },
  onLeave: function(retval) {
      if (retval.toInt32() != 0 || this.receivedBytesPointer.isNull()) {
          if (!this.overlapped.isNull()) {
              logWarning('Overlapped sockets are not supported!');
          }
          if (!this.completionRoutine.isNull()) {
              logWarning('Overlapped sockets are not supported!');
          }
          return;
      }

      const receivedSize =  this.receivedBytesPointer.readULong();
      if (receivedSize <= 0) {
          return;
      }
      if (this.buffersCount <= 0) {
          return;
      }

      // Calculate total capacity and buffers data
      let dataToRead = receivedSize;
      let totalCapacity = 0;
      let totalBuffer = new Uint8Array(receivedSize + 0);
      let offset = 0;
      forEachWsaBuf(this.buffers, this.buffersCount, (buffer) => {
          const bufferSize = buffer.readULong();
          const bufferPointer = buffer.add(Process.pointerSize).readPointer(); // 4B ULONG (on x64 +4B alignment)
          totalCapacity += bufferSize;

          // Read data only if there are still data to read
          if (dataToRead <= 0) {
              return;
          }

          // Calculate how much to read from current buffer
          const dataToReadFromBuffer = (dataToRead >= bufferSize) ? bufferSize : dataToRead;

          // Read data and append to total buffer
          const data = Memory.readByteArray(bufferPointer, dataToReadFromBuffer);
          totalBuffer.set(new Uint8Array(data), offset);

          dataToRead -= dataToReadFromBuffer;
          offset += dataToReadFromBuffer;
      });
      
      // Intercept the data
      const response = interceptRecv(getMetadataFromSocket(this.socket, 'wsock'), totalBuffer.buffer);

      // Notify user about shortening of the data
      if (response.data.length > totalCapacity) {
          logInfo('Data will be trimmed from', response.data.length, 'to', totalCapacity, 'in order to fit into app buffers!');
      }

      // Fill the buffers
      let newLength = 0;
      let dataToWrite = response.data;
      forEachWsaBuf(this.buffers, this.buffersCount, (buffer) => {
          if (dataToWrite.length == 0) {
              // No more data to write
              return;
          }

          const bufferSize = buffer.readULong();
          const bufferPointer = buffer.add(Process.pointerSize).readPointer(); // 4B ULONG (on x64 +4B alignment)
          
          // Write to the buffer
          const written = safeWriteToBuffer(bufferPointer, bufferSize, dataToWrite, true);

          // Remove written data from buffer
          dataToWrite = dataToWrite.slice(written);
          
          // Remember length
          newLength += written;
      });

      // Write new size as bytes read
      if (!this.receivedBytesPointer.isNull()) {
          this.receivedBytesPointer.writeULong(newLength);
      }
  }
});

if (module.config.WSARecv) {
  attachToFunctionInLibraries(LIBS, 'WSARecv', () => createWSARecvHandler('WSARecv'));
}

if (module.config.WSARecvFrom) {
  attachToFunctionInLibraries(LIBS, 'WSARecvFrom', () => createWSARecvHandler('WSARecvFrom'));
}

//
// Common Winsock API
//
/*
int WSAAPI shutdown(
  [in] SOCKET s,
  [in] int    how
);

int closesocket(
  [in] SOCKET s
);
*/
const createCloseHandler = (func) => ({
  onEnter: function(args) {
      const socket = args[0].toInt32();
      processClose(getMetadataFromSocket(socket, 'wsock'));
  }, 
  onLeave: function(retval) {
  }
});

if (module.config.closesocket) {
  attachToFunctionInLibraries(LIBS, 'closesocket', () => createCloseHandler('closesocket'));
}

if (module.config.shutdown) {
  attachToFunctionInLibraries(LIBS, 'shutdown', () => createCloseHandler('shutdown'));
}
