package org.res.alightbridge;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.widget.TextView;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.UUID;
import org.json.JSONObject;

/** Discovery receiver. Reads only the URI granted by an Alight share intent. */
public final class ReceiveProjectActivity extends Activity {
    private static final int MAX_BYTES = 1024 * 1024;

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        TextView view = new TextView(this);
        view.setPadding(24, 32, 24, 24);
        view.setTextSize(18);
        setContentView(view);
        // Do not turn recreation into a duplicate receipt.
        if (savedInstanceState != null) {
            view.setText("Recepção encerrada. Consulte o recibo da transferência original.");
            return;
        }
        try {
            Intent intent = getIntent();
            Uri uri = intent.getParcelableExtra(Intent.EXTRA_STREAM);
            if (!Intent.ACTION_SEND.equals(intent.getAction()) || uri == null
                || !"content".equals(uri.getScheme())
                || !"com.alightcreative.app.motion.fileprovider".equals(uri.getAuthority())
                || uri.getLastPathSegment() == null || !uri.getLastPathSegment().endsWith(".xml")
                || (intent.getFlags() & Intent.FLAG_GRANT_READ_URI_PERMISSION) == 0) {
                throw new IllegalArgumentException("Compartilhamento XML do Alight esperado.");
            }
            ByteArrayOutputStream buffer = new ByteArrayOutputStream();
            try (InputStream input = getContentResolver().openInputStream(uri)) {
                if (input == null) throw new IllegalStateException("Arquivo não disponível.");
                byte[] chunk = new byte[8192];
                int count;
                while ((count = input.read(chunk)) != -1) {
                    if (buffer.size() + count > MAX_BYTES) {
                        throw new IllegalArgumentException("XML excede o limite de 1 MiB da prova.");
                    }
                    buffer.write(chunk, 0, count);
                }
            }
            byte[] bytes = buffer.toByteArray();
            if (bytes.length == 0) throw new IllegalArgumentException("Arquivo vazio.");
            File base = getExternalFilesDir(null);
            if (base == null) throw new IllegalStateException("Pasta própria indisponível.");
            String transferId = UUID.randomUUID().toString();
            File folder = new File(new File(base, "exports"), transferId);
            if (!folder.mkdirs()) throw new IllegalStateException("Destino não criado.");
            File project = new File(folder, "project.xml");
            write(project, bytes);
            StringBuilder checksum = new StringBuilder();
            for (byte value : MessageDigest.getInstance("SHA-256").digest(bytes)) {
                checksum.append(String.format(java.util.Locale.ROOT, "%02x", value & 255));
            }
            JSONObject receipt = new JSONObject();
            receipt.put("kind", "alight.shared_xml_transfer.v1");
            receipt.put("transferId", transferId);
            receipt.put("receivedAtUnixMs", System.currentTimeMillis());
            receipt.put("sourceAuthority", uri.getAuthority());
            receipt.put("sourceName", uri.getLastPathSegment());
            receipt.put("sha256", checksum.toString());
            receipt.put("bytes", bytes.length);
            receipt.put("appVersion", getPackageManager()
                .getPackageInfo("com.alightcreative.motion", 0).versionName);
            receipt.put("renderQualification", false);
            receipt.put("workerJob", JSONObject.NULL);
            write(new File(folder, "receipt.json"), receipt.toString(2).getBytes(StandardCharsets.UTF_8));
            view.setText("XML recebido do Alight\n\n" + bytes.length + " bytes\nSHA-256: "
                + checksum + "\n\n" + folder + "\n\nReferência de descoberta; importação e render ainda precisam ser validados.");
        } catch (Exception error) {
            view.setText("XML não recebido.\n\n" + error.getClass().getSimpleName()
                + ": " + error.getMessage());
        }
    }

    private static void write(File path, byte[] bytes) throws java.io.IOException {
        try (FileOutputStream output = new FileOutputStream(path)) {
            output.write(bytes);
            output.getFD().sync();
        }
    }
}
