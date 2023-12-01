const LIBS = ["Secur32.dll"];

const BufferType = {
    DATA: 1,
};

/*
typedef struct _SecBufferDesc {
  unsigned long ulVersion;
  unsigned long cBuffers;
  PSecBuffer    pBuffers;
} SecBufferDesc, *PSecBufferDesc;

typedef struct _SecBuffer {
  unsigned long cbBuffer;
  unsigned long BufferType;
#if ...
  char          *pvBuffer;
#else
  void SEC_FAR  *pvBuffer;
#endif
} SecBuffer, *PSecBuffer;
*/
const interceptDataBuffer = (context, secBufferDescPointer, intercept) => {
    const buffersCount = secBufferDescPointer.add(4).readULong();
    const buffers = secBufferDescPointer.add(8).readPointer();

    let buffer = buffers;
    for (let i = 0; i < buffersCount; ++i) {
        const bufferType = buffer.add(4).readULong();

        // Process intercept for DATA buffers
        if (bufferType == BufferType.DATA) {
            const bufferSize = buffer.readULong();
            const bufferPointer = buffer.add(8).readPointer();
            const data = Memory.readByteArray(bufferPointer, bufferSize);

            const response = intercept(getMetadataFromCode(context, 'schannel'), data);

            // Write to the buffer
            const newLength = safeWriteToBuffer(bufferPointer, bufferSize, response.data);
    
            // Write new size (might not work for some apps)
            buffer.writeULong(newLength);
        }

        // Move to next buffer
        buffer = buffer.add(8 + Process.pointerSize);
    }
}

/*
SECURITY_STATUS SEC_ENTRY EncryptMessage(
  [in]      PCtxtHandle    phContext,
  [in]      unsigned long  fQOP,
  [in, out] PSecBufferDesc pMessage,
  [in]      unsigned long  MessageSeqNo
);
*/
if (module.config.EncryptMessage) {
  attachToFunctionInLibraries(LIBS, 'EncryptMessage', (lib) => ({
      onEnter: function(args) {
          interceptDataBuffer(args[0], args[2], interceptSend);
      }, 
      onLeave: function(retval) {
      }
  }));
}

/*
SECURITY_STATUS SEC_ENTRY DecryptMessage(
  [in]      PCtxtHandle    phContext,
  [in, out] PSecBufferDesc pMessage,
  [in]      unsigned long  MessageSeqNo,
  [out]     unsigned long  *pfQOP
);
*/
if (module.config.DecryptMessage) {
  attachToFunctionInLibraries(LIBS, 'DecryptMessage', (lib) => ({
      onEnter: function(args) {
        this.phContext = args[0];
        this.pMessage = args[1];
      }, 
      onLeave: function(retval) {
          interceptDataBuffer(this.phContext, this.pMessage, interceptRecv);
      }
  }));
}
