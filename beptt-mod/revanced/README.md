# BePTT ReVanced 圖片網址黑名單 patcher

2026-11-16，版本 1.0.0。這是標準 ReVanced `.rvp` 自訂 bytecode patch，另附可手動處理 APK／XAPK 的電腦版入口。

## 每次更新如何保留設定

1. 取得新版、尚未修改的 BePTT APK 或 XAPK。
2. 使用相同 `.rvp` 重新 patch；結構指紋不相容時需要更新 patch，不能保證未知未來版本一定適用。
3. 每次使用**同一套件名稱與同一把私人簽章金鑰**。
4. 以覆蓋更新方式安裝，不先解除安裝、不清除 App 資料。

黑名單仍讀取原版修改包使用的 `beptt_exact_image_filter_v1` SharedPreferences，鍵為 `urls` 與 `enabled`。讀取名單不寫入預設值，已儲存的空名單也會保留。App 的其他設定未被 patch 修改。這些條件適用於已安裝同簽章改版之後的更新；官方簽章版本首次轉入私人簽章版本，仍須另外處理安裝相容性，不能直接保證覆蓋。

Android 同簽章更新原則：[官方 app signing 文件](https://developer.android.com/studio/publish/app-signing)。本次已核對新包與上一版交付包的憑證 SHA-256 一致：

```text
c84a4a781523ea55eaf5175f91045e9c904cee98a40c8d60d2bad82383292c8f
```

## 已配置的 Mac 入口

本機交付資料夾 `BePTT-ReVanced-Patcher`：

- 雙擊 `啟動BePTT修補.command`，將新版 APK／XAPK 拖入終端機視窗後按 Enter。
- 成品放在同資料夾的 `已套用/`。
- 已配置固定簽章，並核對輸出憑證，避免誤換金鑰。
- 不下載 BePTT、不自動安裝、不解除安裝、不產生新金鑰。
- XAPK 會處理主 APK 與原有所有 splits，統一簽章並逐一驗證 16 KiB 對齊。
- 此 Mac 已具備 Python 3 與 OpenJDK。移到其他電腦時，須安裝 Java 17+，並更新 `local-config.json` 的 `java_home` 等本機路徑；隨附 Android build-tools 執行檔為 macOS 版本。

`私人簽章/` 內有相同金鑰的 PKCS12 與 ReVanced BKS 格式，以及密碼檔。整個資料夾應保留並做私人備份；不要將金鑰、密碼或本機設定檔上傳 GitHub。公開原始碼壓縮檔不包含這些檔案。

## Android ReVanced Manager

本 bundle 針對 Patcher 22 API；本次查核的官方 Manager 2.6.0 使用 22 系列，舊版 21 系列不適用。Manager 操作與安裝尚未在真機驗收。

1. 在「Patches／修補程式」加入本機 patch 來源，選擇 `beptt-image-filter-1.0.0.rvp`。目前來源實作接受本機二進位檔；參考[官方來源匯入實作](https://github.com/ReVanced/revanced-manager/blob/v2.6.0/app/src/main/java/app/revanced/manager/ui/component/sources/ImportSourceDialog.kt)。不同 Manager 版本的畫面名稱可能不同。
2. 若要覆蓋本次先前交付的私人簽章版本，在「設定 → 匯入與匯出 → 匯入金鑰儲存庫」使用 `私人簽章/beptt-personal.keystore`，alias 為 `beptt-personal`，密碼取自同資料夾的 `密碼.txt`。參考[官方設定文件](https://github.com/ReVanced/revanced-manager/blob/v2.6.0/docs/2_6_settings.md)。
3. Manager 的金鑰儲存庫是共用設定；若它也用來修補其他 App，先匯出原有簽章備份，再切換 BePTT 簽章；完成後可切回其他 App 原本的簽章。
4. 選擇未修改的完整 APK，勾選 `BePTT exact image URL blacklist`，patch 成功後再覆蓋安裝。
5. 若輸入來自 XAPK／split APK，不能把 base.apk 當成完整通用 APK 單獨安裝。本次已驗證的分割套件流程是上述 Mac 入口；尚未提供或驗證 Manager 直接處理 XAPK 的流程。

若 Manager 回報 patch 失敗，不應安裝該結果。ReVanced CLI 6.0.0 可能在 patch 失敗後仍輸出 APK；電腦版入口額外要求本 patch 的明確成功事件，才會封裝交付檔。

## 相容性策略

- 僅相容套件 `y_studio.ka5983.ptt2`，不寫死版本號或檔案 SHA-256。
- 以文章網址字串、方法參數型別、連結／圖片清單轉換及迴圈指令結構辨識解析點。
- 不依賴 `d30`、`qr5`、`qh2`、`nt0` 等 R8 混淆類別名稱，也不依賴行文字／連結欄位的混淆名稱。
- 設定頁使用未混淆的 Activity 路徑與 Android 方法簽章；Application 用繼承型別與生命週期方法辨識。
- 所有位置必須各自唯一且暫存器結構符合，才修改原有方法。比對不到、多重命中或已套過 patch 時明確報錯。
- 不搬動原方法暫存器編號；在可證明隨後會被覆寫的兩個暫存器讀取原文字與連結，過濾圖片清單後交回原迴圈。
- 新 helper 不引用 BePTT 的混淆類別。Application 初始化 Context，降低後續改名對 helper 的影響。

## 建置 `.rvp`

使用本機明確工具路徑，無須 GitHub Packages token。工具版本：ReVanced CLI 6.0.0（內含 Patcher 22.0.0）、Kotlin compiler 2.3.10、D8/R8 8.3.37、Android API stub jar、JDK 17+（本次 OpenJDK 27）。

```bash
python3 build_bundle.py \
  --cli /path/to/revanced-cli-6.0.0-all.jar \
  --kotlinc /path/to/kotlinc/bin/kotlinc \
  --android-jar /path/to/android.jar \
  --r8 /path/to/r8.jar \
  --java-home /path/to/jdk \
  --work /path/to/new-build-directory \
  --out /path/to/beptt-image-filter-1.0.0.rvp
```

bundle 包含 JVM patch class、Manager 使用的 DEX，以及 `extensions/beptt.rve` helper DEX；不包含原版 APK、官方程式碼、個人金鑰或密碼。Kotlin 編譯旗標配合官方 Patcher 22 的 experimental metadata。

電腦 patcher 的 `-b` 僅用於載入自行建置、未附遠端來源證明的本機 `.rvp`；不更改 APK、Android 裝置的簽章驗證或 Play Integrity。

## 驗證與目前界線

已通過：

- ReVanced CLI 載入並列出 bundle，成功 patch 原始 BePTT 7.3.0。
- 完整 APK／XAPK 電腦流程，包括最終交付資料夾內的入口與相對路徑配置。
- 六組混淆類別及行文字／連結欄位改名的模擬 APK：仍成功 patch。這是相容性模擬，並非真的新版本測試。
- 重複套用，以及故意破壞字串指紋的輸入：patch 失敗且電腦入口不產生交付檔。
- 實際 helper 的 14 項設定保留斷言：讀取先前自訂清單、停用開關、空清單、重新初始化與編輯更新，不寫入或重設設定。
- 原有 22 項完整網址規則測試仍適用。
- 反組譯比較：只有文章解析器、SettingActivity、Application 三個原有類別改變，新增六個自有 helper 類別；無遺失原有類別。Manifest、資源、assets 內容保留。重新簽章時官方來源戳記會移除。
- 20 個 APK 統一使用上一版相同簽章，通過簽章與 16 KiB 對齊驗證。
- 同一把 PKCS12 私鑰轉為 ReVanced BKS，已重新讀取並確認私鑰與憑證相同；未輪替金鑰。

尚未驗證：Android Manager 實際匯入與操作、真機覆蓋安裝及重新啟動後的設定、畫面與線上功能。未知未來 BePTT 版本須重新執行指紋檢查；結構變動超出本 patch 能辨識的範圍時仍需維護 patch。

本目錄程式碼依 GPL-3.0-only 提供，完整條款見 LICENSE。
