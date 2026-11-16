# BePTT 7.3.0 圖片完整網址黑名單 v1

> 已另完成可重新套用的 [ReVanced patcher 與固定簽章更新流程](../revanced/README.md)。需要日後自行 patch 新版本並保留設定時，請使用該版本；本目錄保留最初固定 7.3.0 檔案的建置流程。

2026-11-16 接續 Claude Code 研究，完成可建置的個人自用修改。使用者同意以完整圖片網址精確比對，取代較容易誤判的作者／簽名檔區域判斷。

## 操作

打開 BePTT 的「設定」，點右上角「⋮」選單 →「圖片網址黑名單」。可開關功能、每行增刪一個完整圖片網址；「填入預設」只填入編輯框，仍須按「儲存」。清空名單並儲存即可停止隱藏所有圖片。儲存後退出文章再重新進入。

只有命中的圖片預覽不加入版面及該次解析的圖庫清單；內文、推文及原始文字連結保留。名單存於 App 私有 SharedPreferences，不需要網路、root 權限或額外的 Android 權限。

**比對範圍是所有作者、所有文章及推文。** 同一完整網址在任何位置出現都會被隱藏。不同網址即使圖片內容相同也不會被隱藏；不支援網域封鎖、前綴、正規式、萬用字元，也不會自動抓取作者日後新增的簽名檔圖片。

名單中的網址與 BePTT 產生的圖片候選網址必須完全相同，且須存在於原始文字的完整網址 token 或 OSC8 連結中。HTTP/HTTPS、大小寫、路徑、參數及片段不互換。BePTT 本身可能截去圖片 URL 後方參數；本修改在這種情況選擇保留預覽，以避免誤擋。實際使用時以文章中的直接圖片網址為準。

## 預設名單

來源為 y12544 的公開簽名檔。2026-10-28 的[原始文章搜尋索引](https://www.ptt.cc/bbs/LoL/M.1793158869.A.E82.html)及[轉載頁](https://disp.cc/b/LoL/ij35)列出以下 6 個網址；2026-11-15 的[公開文章索引](https://www.pttweb.cc/bbs/LoL/M.1794725969.A.B3C)亦呈現重複的簽名檔網址。部分全文即時抓取回傳 403，因此來源確認依公開搜尋索引及轉載內容，並非登入 PTT 後逐篇檢查。

```text
https://i.imgur.com/ROoMKD3.jpeg
https://pbs.twimg.com/media/G5oohjna0AAEUUD.jpg
https://i.imgur.com/f940BRg.jpeg
https://pbs.twimg.com/media/G7fNb6Pa8AA64C7.jpg
https://iili.io/BM84n6B.jpg
https://pbs.twimg.com/media/GwhSWS9bEAMnb5W.jpg
```

## 修改位置與限制

- 僅接受 base APK SHA-256 `c8a3fd72d976c8960a8234e59ca8604fa76cdf2ade59f42171178f243f016190`（7.3.0，versionCode 1070300012）。不同檔案拒絕修改。
- `d30.b(qr5, a30)`：建立 `qh2` 圖片預覽前呼叫過濾器。命中即跳過預覽與圖庫清單加入步驟，繼續處理後續圖片及文字連結。
- `SettingActivity.onCreateOptionsMenu`：新增選單入口，沿用原有 Activity，無新增 Manifest 元件。
- 新類別獨立放於 `classes3.dex`；ABI stubs 只供編譯，不打包。其餘原有 `classes2.dex`、Manifest、資源、assets 與原生程式庫內容不變。
- 原研究將 `qr5.b` 直接視為文章作者並不適用：它是行作者，一般內文常為 `--`。本版本不採用該作者判斷。
- 這是預覽過濾器，不是全域網路阻擋器；手動點原文字連結仍能開啟圖片。
- 不更改登入、付費、簽章驗證或 Play Integrity 邏輯。重簽後服務端是否接受仍未經裝置實測；不保證所有原有功能可用。

## 建置

工具：Apktool 3.0.3、JDK（本次為 Homebrew OpenJDK 27）、D8/R8 8.3.37、Android API stub JAR，以及 Android SDK Build Tools 36.0.0。

```bash
python3 patch_apk.py /path/to/base.apk \
  --work /path/to/new-build-dir \
  --android-jar /path/to/android.jar \
  --r8-jar /path/to/r8.jar \
  --java-home /path/to/jdk

python3 package_xapk.py /path/to/original.xapk \
  /path/to/new-build-dir/base-filter-unsigned.apk \
  --work /path/to/new-signing-dir \
  --out /path/to/BePTT-filter.xapk \
  --build-tools /path/to/android-sdk/build-tools/36.0.0 \
  --java-home /path/to/jdk \
  --keystore /private/path/to/personal.p12 \
  --alias your-alias \
  --password-file /private/path/to/password-file
```

腳本不下載工具、不安裝 App，也不包含金鑰。所有 20 個 APK 使用相同個人憑證，先以 `zipalign -P 16` 對齊，再簽章並逐一驗證。順序依 [Android 官方 apksigner 文件](https://developer.android.com/tools/apksigner)。原始 APK 與個人簽章私鑰不應加入公開 repo。

## 安裝前

交付為 XAPK 分割套件，不能把主 APK 當成單獨的通用 APK 安裝。沿用輸入套件的 arm64-v8a 原生程式庫與 xxhdpi 資源配置。

**個人簽章與官方簽章不同，一般 Android 安裝流程無法直接覆蓋官方版；root 本身也不會自動解決簽章差異。** 本次未連接手機，未執行安裝、解除安裝、資料還原或變更任何裝置安全設定。請先保留／匯出重要資料。不要為了安裝而直接解除安裝既有 BePTT；應先確認裝置目前的版本、簽章與既有安裝方式。

若目標裝置沒有原版或已確認可以使用同一個人簽章，解壓 XAPK 後可用標準 `adb install-multiple` 一起安裝主 APK 與所有 splits。既有官方版的資料保留與安裝方式必須依實際裝置處理，不提供未驗證的覆蓋指令。

## 已完成驗證

- 22 項 Java 規則測試：完整命中、OSC8 連結、空名單、重複移除、格式拒絕，以及 query／fragment／路徑／大小寫／scheme／host 差異不誤擋。
- 從本次 APK 的 JADX 輸出擷取原 `b26.a` 方法，在 JVM 執行 6 個預設網址：皆被原解析器辨識並被過濾；加查詢參數的變體與不相關內文圖保留。
- APK 回編成功，再次反組譯。與原版經相同 Apktool 回編的基準比較，原有類別僅 `d30`、`SettingActivity` 有差異。
- 逐 ZIP entry 比較：原有內容僅 `classes.dex` 改變，新增 `classes3.dex`；簽章檔另外更新。
- 20 個 APK 均通過簽章及 16 KiB 對齊驗證，且簽章憑證一致。

**尚未驗證：** Android 真機啟動、設定對話框實際排版、儲存與重啟持續性、實際文章與圖庫顯示、登入／通知／其他線上功能，以及不同簽章下保留官方版資料的安裝方式。以上須有目標裝置才能完成；這份交付屬待真機驗收版本。
