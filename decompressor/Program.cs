// See https://aka.ms/new-console-template for more information
using ComponentAce.Compression.Libs.zlib;

// Create a new zlib stream. This will keep the context across multiple packets.
// Thanks to TibiaAPI for the working zlib version.
ZStream zStream = new ZStream();
zStream.inflateInit(-15);
zStream.deflateInit(-15);

while(true){
    try{
        // Get the cli input.
        var input = Console.ReadLine();

        // Ignore empty lines.
        if(string.IsNullOrEmpty(input)){
            continue;
        }

        // input is a hex string, convert it to a byte array.
        var bytes = input.Split(' ').Select(x => Convert.ToByte(x, 16)).ToArray();

        // Create a memory stream to write the decompressed data to.
        var decompressedBytes = new byte[65536];

        // Decompress the data.
        zStream.next_in = bytes;
        zStream.next_in_index = 0;
        zStream.next_out = decompressedBytes;
        zStream.next_out_index = 0;
        zStream.avail_in = bytes.Length;
        zStream.avail_out = decompressedBytes.Length;

        var ret = zStream.inflate(zlibConst.Z_SYNC_FLUSH);

        if (ret != zlibConst.Z_OK)
        {
            throw new Exception($"zlib inflate failed: {ret}");
        }

        // Length of the decompressed data.
        ushort decompressedLength = (ushort)zStream.next_out_index;

        // Convert the decompressed data to a hex string.
        var decompressedHex = BitConverter.ToString(decompressedBytes).Replace("-", " ");
        decompressedHex = $"{BitConverter.ToString(BitConverter.GetBytes(decompressedLength)).Replace("-", " ")} {decompressedHex}";

        // Write the decompressed data to the console.
        Console.Write(decompressedHex);
    }
    catch(Exception e){
        Console.WriteLine(e.Message);
    }
}
