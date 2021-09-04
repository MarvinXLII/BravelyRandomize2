import os
import hashlib
import sys
import zstandard # Decompress
import zlib # Compress
import hjson
from Utilities import get_filename


class ROM:
    def __init__(self, fileName, patches=None):
        self.file = open(fileName, 'rb')

        # Compression types (zlib, zstd)
        self.file.seek(-0xa0, 2)
        self.compressionTypes = bytearray(self.file.read())
        self.compressionTypes[:4] = b'Zlib'
        self.compressionTypes[0x20:0x24] = bytearray([0]*4)

        # Files
        self.files = {}
        self.fileNames = {}

        # Extracted files
        self.data = {}
        self.isPatched = {}

    def clean(self):
        self.data = {}
        self.isPatched = {}

    def patchFile(self, data, fileName):
        key = self.getFullPath(fileName)
        if self.data[key] != data:
            self.data[key] = data
            self.isPatched[key] = True

    def getFullPath(self, fileName):
        baseName = os.path.basename(fileName)
        if baseName in self.fileNames:
            # Filenames are unique most of the time
            if len(self.fileNames[baseName]) == 1:
                return self.fileNames[baseName][0]
            # When they aren't unique, assume the input is more specific.
            test = [fileName in f for f in self.fileNames[baseName]]
            if sum(test) == 1:
                index = test.index(True)
                return self.fileNames[baseName][index]
            print(self.fileNames[baseName])
            sys.exit(f"Full file path cannot be uniquely determined from {fileName}!")
                    
    def extractFile(self, fileName):
        key = self.getFullPath(fileName)
        if not key:
            return

        f = self.files[key]
        if f['compType']:
            pointers = f['pointers']
            data = bytearray([])
            for start, end in pointers:
                self.file.seek(f['base']+start)
                size = end - start
                tmp = self.readBytes(size)
                try:
                    data += zstandard.decompress(tmp) # compType == 1
                except zstandard.ZstdError:
                    data += zlib.decompress(tmp) # compType == 2 ?
        else:
            pointer = f['base'] + 8*3 + 4 + 20 + 5
            self.file.seek(pointer)
            data = self.readBytes(f['size'])

        self.data[key] = data
        self.isPatched[key] = False
        return self.data[key]

    def compressFile(self, data):
        base = 0
        size = 0x10000
        comp = bytearray([])
        pointers = []
        while base < len(data):
            start = len(comp)
            comp += zlib.compress(data[base:base+size])
            base += size
            end = len(comp)
            pointers.append((start, end))
        return comp, pointers
        
    def readFileEntry(self, fileName):
        assert fileName not in self.files
        f = {}
        f['base'] = self.readInt(8)
        f['size'] = self.readInt(8)
        f['decompSize'] = self.readInt(8)
        f['compType'] = self.readInt(4)
        f['sha1'] = self.readBytes(20) # compressed data
        f['count'] = self.readInt(4)
        f['pointers'] = []
        if f['compType']:
            for _ in range(f['count']):
                f['pointers'].append([
                    self.readInt(8), # base
                    self.readInt(8), # end
                    # end - base == size
                ])
            self.file.seek(5, 1)
        else: # File is not compressed
            assert f['count'] == 0
            self.file.seek(1, 1)
            f['pointers'].append([
                f['base'] + 8*3+4+20+5,
                f['base'] + 8*3+4+20+5 + f['size'],
            ])
        # Store entry
        self.files[fileName] = f

        # Map baseName to full file path (important when there are MANY files!) 
        baseName = os.path.basename(fileName)
        if baseName not in self.fileNames:
            self.fileNames[baseName] = []
        self.fileNames[baseName].append(fileName)

    def readString(self, size):
        if size < 0:
            s = self.readBytes(-size*2)
            return s.decode('utf-16')[:-1]
        s = self.readBytes(size)
        return s.decode('utf-8')[:-1]

    def pakString(self, string):
        size = len(string) + 1
        utf8 = string.encode('utf-8') + bytearray([0])
        # Not sure if utf8 will always work. Return utf16 as needed.
        for c in utf8:
            if c & 0x80:
                return string.encode('utf-16')[2:] + bytearray([0]*2), -size*2
        return utf8, size

    def readInt(self, size):
        return int.from_bytes(self.file.read(size), byteorder='little', signed=True)

    def pakInt(self, value, size=4):
        return value.to_bytes(size, byteorder='little', signed=True)
    
    def readBytes(self, size):
        return self.file.read(size)

    def checkSHA(self, base, size, sha1):
        self.file.seek(base)
        data = self.readBytes(size)
        digest = hashlib.sha1(data).digest()
        return digest == sha1

    def getSHA(self, data):
        return hashlib.sha1(data).digest()

    # PATCHED FILES ONLY
    def getBaseDir(self):
        fileNames = list(filter(lambda key: self.isPatched[key], self.data.keys()))
        comDir = os.path.dirname(os.path.commonprefix(fileNames))
        if not comDir:
            return self.baseDir, comDir
        if comDir[-1] != '/':
            comDir += '/'
            
        return self.baseDir+comDir, comDir
    
    def buildPak(self, output):
        pakFile = bytearray([]) # This points to pakData entries
        pakData = bytearray([]) # This will in include comp/decomp data
        baseDir, comDir = self.getBaseDir()
        baseDirBytes, size = self.pakString(baseDir)
        pakFile += self.pakInt(size)
        pakFile += baseDirBytes
        # Number of files
        pakFile += self.pakInt(sum(self.isPatched.values()))
        # Loop over files
        for key, data in self.data.items():
            # Only include modified files
            if not self.isPatched[key]:
                continue
            base = len(pakData)
            # Filename (relative to the new base directory)
            if comDir:
                tmpDir = key.split(comDir)[-1]
            else:
                # tmpDir = key
                tmpDir = k
            fileName, size = self.pakString(tmpDir)
            pakFile += self.pakInt(size)
            pakFile += fileName
            # Pointers
            pakFile += self.pakInt(base, size=8)
            pakData += self.pakInt(0, size=8)
            # Compress
            x = bytearray([])
            if self.files[key]['compType']:
                # Compress data
                comp, offsets = self.compressFile(data)
                x = self.pakInt(len(comp), size=8)                    # Entry size (compressed)
                x += self.pakInt(len(data), size=8)                   # Decompressed size
                x += self.pakInt(1)                                   # Is compressed?
                x += self.getSHA(comp)                                # SHA1 of (compressed) data
                x += self.pakInt(len(offsets))                        # Number of zipped segments
                pointer = 0x34 + 8*2*len(offsets) + 5                 # Offsets to zipped segments
                for start, end in offsets:
                    x += self.pakInt(pointer + start, size=8)         # Start of entry
                    x += self.pakInt(pointer + end, size=8)           # End of entry (==start of next entry)
                # Max size of decompressed entry
                x += self.pakInt(0, size=1)
                x += self.pakInt(min([len(data), 0x10000]))           # Max size of decompressed entry
                pakFile += x
                pakData += x + comp
            else:
                x += self.pakInt(len(data), size=8)                   # Entry size (decompressed)
                x += self.pakInt(len(data), size=8)                   # Decompressed size
                x += self.pakInt(0)                                   # Is compressed?
                x += self.getSHA(data)                                # SHA1 of (decompressed) data
                x += self.pakInt(0, size=5)                           # Number of zipped segments
                pakFile += x
                pakData += x + data
        # FINISH PAK FILE
        sha = self.getSHA(pakFile)
        fileSize = len(pakFile)
        pakFile += self.pakInt(0, size=17)
        pakFile += self.pakInt(self.magic, size=8)
        pakFile += self.pakInt(len(pakData), size=8)
        pakFile += self.pakInt(fileSize, size=8)
        pakFile += sha
        # Build Pak
        with open(output, 'wb') as file:
            file.write(pakData)
            file.write(pakFile)
            file.write(self.compressionTypes)


class ROM_SWITCH(ROM):
    def __init__(self, fileName):
        super(ROM_SWITCH, self).__init__(fileName)

        # Load pointers to files
        self.file.seek(-44 - 0xa0, 2)
        self.magic = self.readInt(8)
        self.fileSectionStart = self.readInt(8)
        self.fileSectionSize = self.readInt(8)
        self.fileSectionSHA1 = self.readBytes(20)
        assert self.checkSHA(self.fileSectionStart, self.fileSectionSize, self.fileSectionSHA1)
        
        # Setup for reading entries
        self.file.seek(self.fileSectionStart)
        size = self.readInt(4)
        self.baseDir = self.readString(size)
        self.file.seek(4, 1) # Number of files (== len(self.files))

        # Read entries
        while self.file.tell() < self.fileSectionStart + self.fileSectionSize:
            self.readFileEntry()

    def readFileEntry(self):
        size = self.readInt(4)
        fileName = self.readString(size)
        super(ROM_SWITCH, self).readFileEntry(fileName)


class ROM_PC(ROM):
    def __init__(self, fileName): # NO PATCHES FOR PC!
        super(ROM_PC, self).__init__(fileName)

        # Check SHA
        self.file.seek(-44 - 0xa0, 2)
        self.magic = self.readInt(8)
        self.file.seek(0x10, 1)
        sha = self.readBytes(20)
        assert int.from_bytes(sha, byteorder='big') == 0xe003b74f42a8556489a87f24644c3bb18d6af4f3

        # Pointers and files
        self.pointers = hjson.load(open(get_filename('json/pointers.json'),'r'))
        self.baseDir = '../../../'

        # Read entries
        for fileName, pointer in self.pointers.items():
            self.file.seek(pointer)
            self.readFileEntry(fileName)

    def readFileEntry(self, fileName):
        super(ROM_PC, self).readFileEntry(fileName)
        self.files[fileName]['base'] = self.pointers[fileName]
