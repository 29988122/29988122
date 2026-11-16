import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.KeyStore;
import java.security.MessageDigest;
import org.bouncycastle.jce.provider.BouncyCastleProvider;

/** Convert a personal PKCS12 key to ReVanced's BKS format, without rotating it. */
public final class ConvertKeystore {
    public static void main(String[] args) throws Exception {
        if (args.length != 4) throw new IllegalArgumentException("input.p12 password-file output.keystore alias");
        char[] password = new String(Files.readAllBytes(Paths.get(args[1])), "UTF-8").trim().toCharArray();
        KeyStore original = KeyStore.getInstance("PKCS12");
        try (java.io.InputStream in = Files.newInputStream(Paths.get(args[0]))) { original.load(in, password); }
        KeyStore target = KeyStore.getInstance("BKS", new BouncyCastleProvider());
        target.load(null, null);
        target.setKeyEntry(args[3], original.getKey(args[3], password), password, original.getCertificateChain(args[3]));
        try (java.io.OutputStream out = Files.newOutputStream(Paths.get(args[2]))) { target.store(out, null); }
        KeyStore verified = KeyStore.getInstance("BKS", new BouncyCastleProvider());
        try (java.io.InputStream in = Files.newInputStream(Paths.get(args[2]))) { verified.load(in, null); }
        if (!java.util.Arrays.equals(verified.getKey(args[3], password).getEncoded(), original.getKey(args[3], password).getEncoded())) {
            throw new IllegalStateException("Private key changed during conversion");
        }
        byte[] digest = MessageDigest.getInstance("SHA-256").digest(verified.getCertificate(args[3]).getEncoded());
        StringBuilder hex = new StringBuilder();
        for (byte b : digest) hex.append(String.format("%02x", b & 255));
        System.out.println("Same key verified. Certificate SHA256: " + hex);
        java.util.Arrays.fill(password, '\0');
    }
}
