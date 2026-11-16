import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.DialogInterface;
import android.content.SharedPreferences;
import android.text.InputType;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import java.util.List;
import java.util.ArrayList;

/** Local-only preview filter, with an editor in the existing settings menu. */
public final class BepttImageFilter {
    private static final String PREFS = "beptt_exact_image_filter_v1";
    private static final String DEFAULTS =
        "https://i.imgur.com/ROoMKD3.jpeg\n"
        + "https://pbs.twimg.com/media/G5oohjna0AAEUUD.jpg\n"
        + "https://i.imgur.com/f940BRg.jpeg\n"
        + "https://pbs.twimg.com/media/G7fNb6Pa8AA64C7.jpg\n"
        + "https://iili.io/BM84n6B.jpg\n"
        + "https://pbs.twimg.com/media/GwhSWS9bEAMnb5W.jpg";
    private static String cachedText;
    private static BepttUrlRules cachedRules;

    private static SharedPreferences prefs(Context context) {
        return context.getApplicationContext().getSharedPreferences(PREFS, 0);
    }

    private static volatile Context applicationContext;

    public static void initialize(Context context) {
        applicationContext = context.getApplicationContext();
    }

    public static synchronized List<String> filter(List<String> candidates, String rawText, List<?> links) {
        try {
            Context context = applicationContext;
            if (context == null) return candidates;
            SharedPreferences prefs = prefs(context);
            if (!prefs.getBoolean("enabled", true)) return candidates;
            String text = prefs.getString("urls", DEFAULTS);
            if (!text.equals(cachedText)) {
                cachedRules = new BepttUrlRules(text);
                cachedText = text;
            }
            ArrayList<String> visible = new ArrayList<String>(candidates.size());
            for (String candidate : candidates) {
                if (!cachedRules.hides(candidate, rawText, links)) visible.add(candidate);
            }
            return visible;
        } catch (RuntimeException invalidState) {
            return candidates;
        }
    }

    public static void addSettingsMenu(Menu menu, final Activity activity) {
        initialize(activity);
        MenuItem item = menu.add(0, 0x6b700001, 100, "圖片網址黑名單");
        item.setShowAsAction(MenuItem.SHOW_AS_ACTION_NEVER);
        item.setOnMenuItemClickListener(new MenuItem.OnMenuItemClickListener() {
            public boolean onMenuItemClick(MenuItem item) {
                showEditor(activity);
                return true;
            }
        });
    }

    private static void showEditor(final Activity activity) {
        final SharedPreferences prefs = prefs(activity);
        LinearLayout body = new LinearLayout(activity);
        body.setOrientation(LinearLayout.VERTICAL);
        int pad = (int) (20 * activity.getResources().getDisplayMetrics().density);
        body.setPadding(pad, pad / 2, pad, pad / 2);
        final CheckBox enabled = new CheckBox(activity);
        enabled.setText("啟用圖片網址黑名單");
        enabled.setChecked(prefs.getBoolean("enabled", true));
        body.addView(enabled);
        TextView help = new TextView(activity);
        help.setText("每行一個完整圖片網址，完全相同才隱藏預覽。文字連結保留；同一網址在任何作者的文章或推文都會隱藏。\n\n預設為 y12544 公開簽名檔的 6 個圖片網址，可自由刪改。清空名單即可全部顯示。儲存後請退出文章再重新開啟。");
        body.addView(help);
        final EditText editor = new EditText(activity);
        editor.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE | InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);
        editor.setSingleLine(false);
        editor.setMinLines(6);
        editor.setText(prefs.getString("urls", DEFAULTS));
        editor.setTextSize(14);
        body.addView(editor);
        ScrollView scroll = new ScrollView(activity);
        scroll.addView(body);
        final AlertDialog dialog = new AlertDialog.Builder(activity)
            .setTitle("圖片網址黑名單")
            .setView(scroll)
            .setPositiveButton("儲存", null)
            .setNegativeButton("取消", null)
            .setNeutralButton("填入預設", null)
            .create();
        dialog.setOnShowListener(new DialogInterface.OnShowListener() {
            public void onShow(DialogInterface ignored) {
                dialog.getButton(AlertDialog.BUTTON_NEUTRAL).setOnClickListener(new View.OnClickListener() {
                    public void onClick(View view) { editor.setText(DEFAULTS); }
                });
                dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(new View.OnClickListener() {
                    public void onClick(View view) {
                        try {
                            BepttUrlRules rules = new BepttUrlRules(editor.getText().toString());
                            prefs.edit().putString("urls", rules.text())
                                .putBoolean("enabled", enabled.isChecked()).apply();
                            Toast.makeText(activity, "已儲存；請重新開啟文章", Toast.LENGTH_LONG).show();
                            dialog.dismiss();
                        } catch (IllegalArgumentException invalid) {
                            editor.setError(invalid.getMessage());
                        }
                    }
                });
            }
        });
        dialog.show();
    }
}
