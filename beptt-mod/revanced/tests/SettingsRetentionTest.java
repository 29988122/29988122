import android.content.Context;
import android.content.SharedPreferences;
import java.lang.reflect.Proxy;
import java.util.*;

public final class SettingsRetentionTest {
    private static int checks;
    private static void check(boolean ok) { checks++; if (!ok) throw new AssertionError("check " + checks); }
    private static final class SavedContext extends Context {
        final Map<String, Object> saved;
        SavedContext(Map<String, Object> saved) { this.saved = saved; }
        public SharedPreferences getSharedPreferences(String name, int mode) {
            check("beptt_exact_image_filter_v1".equals(name));
            return (SharedPreferences) Proxy.newProxyInstance(getClass().getClassLoader(), new Class<?>[]{SharedPreferences.class}, (proxy, method, args) -> {
                if (method.getName().equals("getString") || method.getName().equals("getBoolean")) return saved.containsKey(args[0]) ? saved.get(args[0]) : args[1];
                throw new AssertionError("Unexpected preference write or call: " + method.getName());
            });
        }
    }
    public static void main(String[] args) throws Exception {
        String custom = "https://example.org/user-saved.jpg";
        String originalDefault = "https://i.imgur.com/ROoMKD3.jpeg";
        List<String> images = Arrays.asList(custom, originalDefault);
        String raw = custom + " " + originalDefault;
        Map<String,Object> saved = new HashMap<>();
        saved.put("urls", custom);
        saved.put("enabled", true);
        BepttImageFilter.initialize(new SavedContext(saved));
        check(BepttImageFilter.filter(images, raw, Collections.emptyList()).equals(Arrays.asList(originalDefault)));
        check(images.size() == 2); // input list remains unchanged
        // Simulate a fresh Application instance after an APK update.
        BepttImageFilter.initialize(new SavedContext(saved));
        check(BepttImageFilter.filter(images, raw, Collections.emptyList()).equals(Arrays.asList(originalDefault)));
        check(custom.equals(saved.get("urls"))); // defaults never overwrite a saved list
        saved.put("enabled", false);
        check(BepttImageFilter.filter(images, raw, null) == images);
        saved.put("enabled", true);
        saved.put("urls", "");
        check(BepttImageFilter.filter(images, raw, null).equals(images));
        saved.put("urls", originalDefault);
        check(BepttImageFilter.filter(images, raw, null).equals(Arrays.asList(custom))); // live edit refresh
        saved.put("urls", "invalid URL");
        check(BepttImageFilter.filter(images, raw, null) == images); // fail open on bad state
        System.out.println("PASS: " + checks + " actual helper/settings retention assertions; no preference writes");
    }
}
