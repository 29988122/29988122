# BePTT 圖片網址黑名單 Xposed 模組

模組套件 `net.beptt.imagefilter` 獨立於 Play 商店的 BePTT。作用範圍固定為 `y_studio.ka5983.ptt2`。從模組的設定畫面管理完整圖片網址，沿用前版的六個預設網址。BePTT 的 APK、選單、簽章和設定檔不需改動。

## 安裝與設定

1. 使用已具備 libxposed API 101 或更新版與遠端設定服務的 Vector／LSPosed 環境。模組 APK 需要 Android 8.0 以上，框架本身另有系統與 root 環境要求。[Vector 安裝需求](https://github.com/JingMatrix/Vector#installation)
2. 安裝 `BePTT-Image-Filter-Xposed-1.0.0.apk`，在 Xposed 管理器啟用模組，確認作用範圍勾選 BePTT。
3. 打開獨立的「BePTT 圖片網址黑名單」App。可直接貼上網址，或選擇「匯入文字檔」，從手機／Dropbox 選一份 UTF-8 檔案。每行一個完整圖片網址，按「儲存設定」才會套用。上限 64 KiB。
4. 首次啟用模組後強制停止並重開 BePTT。平常編輯名單後重新開啟文章即可。可匯出名單做備份，或從之前的 ReVanced 改版複製已儲存的網址。

名單由 Xposed 的遠端設定服務保存在獨立模組的設定群組。Google Play 更新 BePTT 後，重新啟動 App 即會針對新的 APK 找出圖片解析位置，名單繼續沿用。若目前手機上已有私人簽章的 BePTT，這個模組可用於支援的既有版本，但該安裝仍須先回到官方簽章才能恢復 Play 更新。切換前先備份舊資料。

## 過濾範圍

- 只有完整網址相同的圖片預覽會被過濾，同一網址出現在其他作者、本文或推文也適用。原始文字和可點選的文字連結保留。
- 名單只在本機讀取。Dropbox 是檔案來源之一，選檔時由 Android 檔案選擇器處理。模組無背景網址同步。
- 清空名單或關閉模組設定的核取方塊即可恢復預覽。沒有舊名單時會使用內建預設。
- 靜態比對使用文章網址提示、兩個文字／連結欄位、兩次相鄰的清單轉換，以及後續迴圈結構。執行時只在該解析方法直接呼叫轉換器的第二次呼叫過濾結果。
- 比對不到唯一目標或框架設定不可用時，保留原始行為。Xposed 日誌中的 `BePTT Image Filter` 可查看結構命中、首次實際過濾或初始化失敗。新版變更解析方式時可能需要更新模組。

## 建置與驗證

建置使用 JDK 11 以上（本次為 OpenJDK 27）、Android SDK Platform 36 的 `android.jar`、Build Tools 36.0.0，以及下列 Maven Central 依賴。三個 libxposed AAR 請先取出 `classes.jar`，依下載檔名存為相應的 `.jar`。

| 依賴 | 版本 |
|---|---|
| `io.github.libxposed:api`（僅編譯） | 102.0.0 |
| `io.github.libxposed:service`、`io.github.libxposed:interface` | 102.0.0 |
| `org.smali:dexlib2` | 2.5.2 |
| `com.google.guava:guava`、`com.google.guava:failureaccess` | 27.1-android、1.0.1 |

`build_module.py --help` 可列出工具和簽章所需參數。與 ReVanced 版共用 `../patch/src/BepttUrlRules.java`，模組金鑰獨立於 BePTT 改版金鑰，應保留供模組更新。

已驗證產出 APK 可通過簽章與對齊檢查，也在 JVM 直接對原版 BePTT 7.3.0 驗證找到解析器和轉換器。混淆類別與欄位改名的合成測試包仍能辨識，破壞結構的測試包會被拒絕。共用規則有 22 項網址測試。Android 框架實際執行 hook、檔案匯入與 Play 覆蓋更新須在連接的手機上驗收。
