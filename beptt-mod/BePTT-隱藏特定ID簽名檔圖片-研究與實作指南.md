# BePTT 自訂功能研究:隱藏特定 ID 的簽名檔/內嵌圖片

> 目標:當文章(或推文)的作者是某些你指定的 ID 時,**不要渲染該文中被自動展開的圖片預覽**,
> 因為那些圖片很佔版面。保留文字照常閱讀,只是把圖「關掉」。

---

## 0. 基本情報(已確認)

| 項目 | 內容 |
|---|---|
| App 名稱 | BePTT |
| Android 套件名 | `y_studio.ka5983.ptt2` |
| 開發者 | Yan Kai Huang / Y Studio Lab(**閉源**,非開源專案) |
| Google Play | https://play.google.com/store/apps/details?id=y_studio.ka5983.ptt2 |
| 既有相關功能 | **黑名單 / 白名單**、**自動開啟圖片/預覽網址**(內嵌縮圖) |

兩個對我們極有利的事實:
1. App 已經有「**黑名單(封鎖特定使用者)**」機制 → 代表程式裡**已經有「拿到某則文章/推文的作者 ID,再去比對一份名單」的現成邏輯**。我們幾乎可以照抄這段,只是把「比對結果 = 不顯示整篇」改成「比對結果 = 不顯示圖片」。
2. App 已經有「**自動開啟圖片/預覽**」→ 程式裡**已經有「把內文裡的圖片 URL 變成一個可見的圖片 View / 縮圖」的現成進入點**。我們要做的,就是在這個進入點前面加一道判斷。

所以這個改動的本質是:**在「圖片即將被渲染」的那一刻,插入一個 `if (作者 ID ∈ 我的圖片黑名單) return;`**。

---

## 1. 取得 APK(從你自己已 root 的裝置,最乾淨)

不要去抓來路不明的鏡像。你有 root,直接從裝置撈出你正在用的那版:

```bash
# 在電腦上(adb 已連線到手機,手機已開 USB 偵錯)
# 1) 找出 base apk 路徑
adb shell pm path y_studio.ka5983.ptt2
# 會印出類似:
#   package:/data/app/~~xxxx==/y_studio.ka5983.ptt2-yyyy==/base.apk
#   (若有 split_config.* 那幾行,代表是 App Bundle 拆包,見下方註)

# 2) 把 base.apk 拉回電腦
adb pull /data/app/.../base.apk ./beptt-base.apk

# 若上一步因權限不足,改用 root:
adb shell su -c "cp /data/app/.../base.apk /sdcard/beptt-base.apk"
adb pull /sdcard/beptt-base.apk ./beptt-base.apk
```

> **App Bundle 註**:若 `pm path` 回傳不只 `base.apk`,還有 `split_config.arm64_v8a.apk`、`split_config.xxhdpi.apk` 等,
> 代表它是 AAB 動態交付。改圖片邏輯通常只需動 `base.apk`(程式碼都在 base),但**安裝時要把所有 split 一起裝回去**
> (見第 6 節的 `install-multiple`),否則資源/原生庫會缺。

驗證拿到的是對的檔:
```bash
unzip -p beptt-base.apk AndroidManifest.xml | strings | grep -i ptt   # 粗略確認
# 或用 aapt dump badging beptt-base.apk | head   (需 build-tools)
```

---

## 2. 工具鏈(在你自己的機器上安裝)

| 工具 | 用途 | 取得 |
|---|---|---|
| JDK 17+ | 跑所有 jar | 系統套件 |
| **apktool** 2.10+ | 反編譯(資源+smali)、回編譯 | https://github.com/iBotPeaches/Apktool/releases |
| Android **build-tools**(aapt2 / zipalign / apksigner) | 對齊 + 簽章 | Android SDK(sdkmanager) |
| **uber-apk-signer**(可選,一鍵對齊+簽) | 省掉手動 zipalign/apksigner | https://github.com/patrickfav/uber-apk-signer/releases |
| jadx(**強烈建議**) | 把 APK 反編譯成**可讀 Java**,用來「看懂邏輯、找定位」 | https://github.com/skylot/jadx/releases |

分工心法:**用 jadx 看懂程式、找到要改的地方(對照可讀 Java);用 apktool 改 smali、回編譯**。
(jadx 的 Java 多半不能直接編回去,所以真正下刀是在 apktool 產生的 `.smali`。)

> 註:本雲端 session 已先幫你把 `apktool.jar`、`uber-apk-signer.jar` 下載在 `beptt-mod/tools/`,
> 但在此環境「執行」這些重打包工具會被自動審核擋下,所以請在你自己的機器上跑。

---

## 3. 反編譯

```bash
# 產生一份「反組譯」目錄(smali + 資源),之後要回編譯的就是這份
java -jar apktool.jar d beptt-base.apk -o beptt_src

# 另外用 jadx 產一份可讀 Java 來「研究定位」(不回編)
jadx -d beptt_jadx beptt-base.apk    # 或開 jadx-gui 直接搜尋
```

目錄重點:
- `beptt_src/smali*/...` → 要改的程式碼(可能有 `smali`, `smali_classes2`...)
- `beptt_src/res/` → 版面與設定畫面(若之後想在設定裡加 UI 開關會動到)
- `beptt_src/AndroidManifest.xml`、`apktool.yml` → 回編譯設定

---

## 4. 定位:找到「圖片渲染點」與「作者 ID」

這是整個工作的核心。因為是閉源且幾乎確定有 **R8/ProGuard 混淆**(class/method 名會變成 `a`, `b`, `c`),
不能靠猜類名,要靠**字串/API 這些混淆不掉的錨點**去追。到 jadx-gui 用全域搜尋(或對 smali 用 `grep -rn`)。

### 4-1. 先定位「圖片是怎麼被顯示的」
搜尋這些**不會被混淆的錨點**:

```bash
cd beptt_src
# 影像載入框架(找出它用哪一套)
grep -rn "com/bumptech/glide" smali*        # Glide
grep -rn "coil" smali*                        # Coil(Kotlin 常用)
grep -rn "squareup/picasso" smali*            # Picasso
grep -rn "facebook/drawee\|fresco" smali*     # Fresco
# 常見圖床 / URL 偵測
grep -rn "imgur" smali*
grep -rn "i\.imgur\|\.jpg\|\.png\|\.gif\|\.webp" smali*
# WebView 方式顯示圖片的話
grep -rn "loadUrl\|WebView" smali*
```

幾乎所有 Android App 顯示網路圖片都會經過上面某一套。找到後,**往上追呼叫端**:
誰在「拿到一個 URL → 丟給 Glide/Coil `.load(url).into(imageView)`」。那個呼叫點,就是我們要下刀的「圖片渲染點」。
通常它會在:
- 文章內文的 RecyclerView adapter 的 `onBindViewHolder`(每一行/每個連結一個 item),或
- 一個把「偵測到的連結」轉成「縮圖卡片」的 helper。

### 4-2. 再定位「作者 ID 從哪裡拿」
利用**既有的黑名單功能**當跳板——它一定要能「拿到作者 ID 並比對名單」:

```bash
# 從設定字串反查(黑名單畫面的文字 → 對應的 class)
grep -rn "黑名單\|blacklist\|block" smali* res/values*/strings.xml
grep -rn "白名單\|whitelist" smali* res/values*/strings.xml
```

1. 在 `res/values*/strings.xml` 找到「黑名單」那串字的 **resource id**(如 `R.string.xxx`)。
2. 用那個 id(smali 裡是 `const ... 0x7f0yxxxx`,或在 `public.xml` 可查到名稱)反查是哪個設定頁。
3. 進去看黑名單**實際比對作者**的那段:它會有一個「取得作者 ID 的 getter」和「名單 contains() 判斷」。
   把這兩個東西記下來——**它們就是你要在圖片渲染點重用的零件**:
   - `getAuthorId(article)`:怎麼從一則文章/推文物件拿到作者字串。
   - `blacklist.contains(id)`:名單資料結構與比對方式。

> 小技巧:直接在 jadx-gui 對「黑名單」字串 → Find Usage,一路點進去看 Java,比盲讀 smali 快十倍。
> 看懂後再回 apktool 的 smali 對應位置下刀。

---

## 5. 實作策略(三種,從簡到繁,擇一)

### 方案 A(最省事、最穩):在「圖片渲染點」加作者判斷,命中就不渲染
在第 4-1 找到的 `.into(imageView)` / `loadUrl` **之前**,插入:

```
if (作者ID ∈ 我的圖片黑名單) {
    // 不載入;並把該圖片 View 設為 GONE,避免佔位空白
    imageView.setVisibility(View.GONE);
    return;
}
// 原本的載入流程...
```

對應的 smali(示意,類名/暫存器請依實際調整):假設此處有 `imageView`(`v2`)與可取得作者的物件(`v0`),
而你已把「判斷函式」做成一個自己的小工具類 `Lme/mymod/ImgFilter;`(見下),則插入:

```smali
    # ---- begin mod ----
    invoke-static {v0}, Lme/mymod/ImgFilter;->shouldHide(Ljava/lang/Object;)Z
    move-result v9
    if-eqz v9, :img_filter_pass
    const/16 v9, 0x8                      # View.GONE
    invoke-virtual {v2, v9}, Landroid/view/View;->setVisibility(I)V
    return-void                            # 或 goto 跳過載入段(視 method 結構)
    :img_filter_pass
    # ---- end mod ----
    # ... 原本 Glide/Coil .into(...) 的指令接在這 ...
```

把判斷邏輯集中在一個**自己新增的 smali 類**,未來維護只改這一個檔、名單也放這:

`beptt_src/smali/me/mymod/ImgFilter.smali`(可先寫 Java 用 `d8`/`javac`→轉 smali,或直接手寫)。
名單建議先寫死(hardcode)最快;想之後能在 App 內改,再接到 SharedPreferences(見方案 C)。

> **granularity 取捨**:方案 A 會把「該作者文章內的所有圖片」都藏掉(含簽名檔與內文圖)。
> 對你的需求(簽名檔那張固定廣告式的圖很煩)通常這樣最乾脆。
> 若你**只**想藏簽名檔、保留內文圖,見方案 B。

### 方案 B(只藏簽名檔區域的圖):加一個「是否位於簽名檔」判斷
PTT 文章沒有結構化的「簽名欄位」,簽名檔只是內文結尾、通常在最後一條 `-- ` 分隔線之後的那幾行。
作法:在內文解析/切行的地方,標記「此行是否在最後一個 `--` 之後」(isInSignature),
渲染圖片時改成 `if (作者ID命中 && isInSignature) 不顯示`。
成本:要找到切行/解析內文的程式碼並多帶一個旗標,比 A 複雜。除非你很在意內文圖要保留,否則用 A。

### 方案 C(做成 App 內可編輯的名單 + 開關,最完整)
- 在設定頁(找黑名單那頁的 layout/adapter)旁邊複製一份,做「圖片黑名單」。
- 名單存 `SharedPreferences`;`ImgFilter.shouldHide()` 改成讀 prefs。
- 工作量最大(要動 res/layout、字串、設定 adapter),但一次做好、之後加 ID 不用重編 APK。
- 建議**先用 A 驗證可行**,確定能藏圖了,再考慮升級成 C。

---

## 6. 回編譯、對齊、簽章、安裝

```bash
# 回編譯
java -jar apktool.jar b beptt_src -o beptt-mod-unsigned.apk

# 一鍵對齊 + 簽(uber-apk-signer 會自動產生 debug keystore)
java -jar uber-apk-signer.jar -a beptt-mod-unsigned.apk --allowResign
# 產出 beptt-mod-unsigned-aligned-debugSigned.apk

# —— 或手動 ——
zipalign -p -f 4 beptt-mod-unsigned.apk beptt-mod-aligned.apk
# 自備 keystore(第一次):
keytool -genkey -v -keystore my.keystore -alias mod -keyalg RSA -keysize 2048 -validity 10000
apksigner sign --ks my.keystore --out beptt-mod-signed.apk beptt-mod-aligned.apk
apksigner verify --print-certs beptt-mod-signed.apk
```

**安裝(你有 root,這是關鍵優勢)**:因為換了簽章,和官方版簽章不同,無法直接 `-r` 覆蓋安裝。兩條路:

```bash
# (路線一)最簡單:先移除官方版再裝改機版
adb uninstall y_studio.ka5983.ptt2            # ⚠ 會清掉 App 資料(含已存帳號)
adb install beptt-mod-signed.apk
# 若原本是多 split:
adb install-multiple base-mod.apk split_config.*.apk

# (路線二)想保留 App 資料:用 root 先備份 /data/data 再還原,或用簽章偽裝框架
adb shell su -c "tar -czf /sdcard/beptt_data.tgz -C /data/data y_studio.ka5983.ptt2"
# ... uninstall / install 改機版 ...
adb shell su -c "tar -xzf /sdcard/beptt_data.tgz -C /data/data && \
  chown -R <uid>:<uid> /data/data/y_studio.ka5983.ptt2"   # uid 以 dumpsys package 查
```

> 你 root 的另一個好處:若想長期維持,可把官方版自動更新關掉(避免更新後覆蓋你的改機版),
> 或把改機版改成**不同套件名**(改 `AndroidManifest` 的 package + `apktool.yml`,較麻煩但能與官方版並存)。

---

## 7. 風險與維護

- **混淆位移**:每次官方更新,smali 的類名/行號都會變,方案 A/B 的插入點要**重找**。把「怎麼找」(第 4 節)的錨點記熟,比記死行號重要。方案 C 把邏輯集中在自建類,受影響較小。
- **帳號資料**:換簽章安裝會洗掉資料,先想好備份(見第 6 節)。
- **法務/條款**:自用、改自己裝置上的 App、不散佈,一般屬個人修改範疇;**不要公開散佈改機 APK**(涉著作權與商標)。
- **崩潰排查**:若回編後閃退,先 `adb logcat | grep -i y_studio` 看 stack;常見是 smali 暫存器用錯(`v`/`p` 編號、`.registers` 不足)或 `return` 跳錯位置。

---

## 8. 一頁式 checklist

1. `adb` 從自己 root 裝置 pull `base.apk`(+ 任何 split)。
2. `apktool d` 反編譯;`jadx` 另產可讀 Java 供研究。
3. 搜錨點:Glide/Coil/Picasso/imgur/WebView → 找「圖片渲染點」;搜「黑名單」字串 → 找「取作者ID + 比名單」的現成零件。
4. 新增 `me/mymod/ImgFilter.smali`,在渲染點前插 `shouldHide` 判斷(方案 A)。
5. `apktool b` → `zipalign` → `apksigner`(或 uber-apk-signer 一鍵)。
6. root 裝置:備份資料 → `uninstall` 官方 → `install(-multiple)` 改機版 → 還原資料。
7. `logcat` 驗證、關自動更新。
```
