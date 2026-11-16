package tw.beptt.patches

import app.revanced.patcher.patch.bytecodePatch
import app.revanced.patcher.patch.PatchException
import app.revanced.patcher.extensions.InstructionExtensions.addInstructions
import app.revanced.com.android.tools.smali.dexlib2.mutable.MutableMethod
import com.android.tools.smali.dexlib2.Opcode
import com.android.tools.smali.dexlib2.iface.ClassDef
import com.android.tools.smali.dexlib2.iface.Method
import com.android.tools.smali.dexlib2.iface.instruction.*
import com.android.tools.smali.dexlib2.iface.reference.*

private const val HELPER = "LBepttImageFilter;"
private const val LIST = "Ljava/util/List;"

private fun fail(message: String): Nothing = throw PatchException("BePTT URL filter: $message. No compatible output was produced; use an unpatched official APK or update this patch.")
private fun Instruction.methodRef() = (this as? ReferenceInstruction)?.reference as? MethodReference
private fun Instruction.fieldRef() = (this as? ReferenceInstruction)?.reference as? FieldReference
private fun Instruction.string() = ((this as? ReferenceInstruction)?.reference as? StringReference)?.string
private fun Method.code() = implementation?.instructions?.toList().orEmpty()
private fun Method.sameSignature(other: Method) = name == other.name && parameterTypes == other.parameterTypes && returnType == other.returnType

private data class ImageSite(
    val method: Method,
    val index: Int,
    val images: Int,
    val record: Int,
    val rawScratch: Int,
    val linksScratch: Int,
    val text: FieldReference,
    val links: FieldReference,
)

private fun findImageSite(method: Method): ImageSite {
    val code = method.code()
    if (code.any { it.methodRef()?.definingClass == HELPER }) fail("input is already patched")
    if (method.returnType != "V" || method.parameterTypes.size != 2) fail("article parser signature changed")
    val recordType = method.parameterTypes.first().toString()
    val fields = code.mapNotNull { instruction ->
        if (instruction.opcode != Opcode.IGET_OBJECT) null else {
            val field = instruction.fieldRef()
            if (field?.definingClass == recordType) instruction to field else null
        }
    }
    val text = fields.firstOrNull { it.second.type == "Ljava/lang/String;" } ?: fail("line text field missing")
    val links = fields.firstOrNull { it.second.type == LIST } ?: fail("line links field missing")
    val record = (text.first as TwoRegisterInstruction).registerB
    if ((links.first as TwoRegisterInstruction).registerB != record) fail("line fields no longer share a receiver")

    fun isListConversion(instruction: Instruction): Boolean {
        val ref = instruction.methodRef() ?: return false
        return instruction.opcode == Opcode.INVOKE_STATIC && ref.returnType == LIST &&
            ref.parameterTypes.map { it.toString() } == listOf("Ljava/lang/Iterable;")
    }
    val matches = (0 until code.size - 7).mapNotNull { index ->
        if (!isListConversion(code[index]) || !isListConversion(code[index + 2]) ||
            code[index].methodRef().toString() != code[index + 2].methodRef().toString() ||
            code[index + 1].opcode != Opcode.MOVE_RESULT_OBJECT ||
            code[index + 3].opcode != Opcode.MOVE_RESULT_OBJECT ||
            code[index + 4].opcode != Opcode.MOVE ||
            code[index + 5].opcode != Opcode.INVOKE_INTERFACE ||
            code[index + 6].opcode != Opcode.MOVE_RESULT || code[index + 7].opcode != Opcode.IF_GE) return@mapNotNull null
        val size = code[index + 5].methodRef() ?: return@mapNotNull null
        if (size.definingClass != LIST || size.name != "size" || size.returnType != "I" || size.parameterTypes.isNotEmpty()) return@mapNotNull null
        val otherList = (code[index + 1] as OneRegisterInstruction).registerA
        val images = (code[index + 3] as OneRegisterInstruction).registerA
        val rawScratch = (code[index + 4] as TwoRegisterInstruction).registerA
        val zero = (code[index + 4] as TwoRegisterInstruction).registerB
        val linksScratch = (code[index + 6] as OneRegisterInstruction).registerA
        val comparison = code[index + 7] as TwoRegisterInstruction
        if ((code[index + 5] as FiveRegisterInstruction).registerC != otherList ||
            comparison.registerA != rawScratch || comparison.registerB != linksScratch) return@mapNotNull null
        // Both scratch registers are overwritten by the original loop immediately
        // after insertion. Never allocate registers or rewrite parameter numbering.
        if (setOf(images, record, rawScratch, linksScratch, otherList, zero).size != 6 ||
            listOf(images, record, rawScratch, linksScratch).any { it !in 0..15 }) return@mapNotNull null
        ImageSite(method, index + 4, images, record, rawScratch, linksScratch, text.second, links.second)
    }
    return matches.singleOrNull() ?: fail("image list structural fingerprint matched ${matches.size} locations instead of one")
}

@Suppress("unused", "DEPRECATION")
val bepttExactImageUrls = bytecodePatch(
    name = "BePTT exact image URL blacklist",
    description = "Hide exact image URLs with an editable in-app blacklist. Retains existing blacklist settings on same-signer updates. Fails if structural fingerprints change.",
) {
    compatibleWith("y_studio.ka5983.ptt2")
    extendWith("extensions/beptt.rve")
    apply {
        val parserMatches = classDefs.flatMap { owner -> owner.methods.filter { method ->
            method.returnType == "V" && method.parameterTypes.size == 2 &&
                method.parameterTypes.all { it.startsWith("L") } &&
                method.code().any { it.string() == "※ 文章網址:" }
        }.map { owner to it } }
        val (parserClass, parserMethod) = parserMatches.singleOrNull()
            ?: fail("article parser fingerprint matched ${parserMatches.size} methods instead of one")
        val site = findImageSite(parserMethod)

        val settingMatches = classDefs.flatMap { owner ->
            if (!owner.type.endsWith("/presentation/setting/SettingActivity;")) emptyList() else owner.methods.filter {
                it.name == "onCreateOptionsMenu" && it.parameterTypes.map { p -> p.toString() } == listOf("Landroid/view/Menu;") && it.returnType == "Z"
            }.map { owner to it }
        }
        val (settingClass, settingMethod) = settingMatches.singleOrNull() ?: fail("settings menu fingerprint is not unique")
        val appMatches = classDefs.filter {
            it.type.startsWith("Ltw/ystudio/beptt/") && it.superclass == "Landroid/app/Application;"
        }.flatMap { owner -> owner.methods.filter {
            it.name == "onCreate" && it.parameterTypes.isEmpty() && it.returnType == "V"
        }.map { owner to it } }
        val (appClass, appMethod) = appMatches.singleOrNull() ?: fail("Application lifecycle fingerprint is not unique")
        if (listOf(settingMethod, appMethod).any { m -> m.code().any { it.methodRef()?.definingClass == HELPER } }) fail("input is already patched")
        if (settingMethod.implementation == null || appMethod.implementation == null) fail("lifecycle method has no code")

        fun mutable(owner: ClassDef, method: Method): MutableMethod = classDefs.getOrReplaceMutable(owner).methods.single { it.sameSignature(method) }
        // All fingerprints must validate before changing any original method.
        mutable(parserClass, parserMethod).addInstructions(site.index, """
            iget-object v${site.rawScratch}, v${site.record}, ${site.text}
            iget-object v${site.linksScratch}, v${site.record}, ${site.links}
            invoke-static {v${site.images}, v${site.rawScratch}, v${site.linksScratch}}, $HELPER->filter(Ljava/util/List;Ljava/lang/String;Ljava/util/List;)Ljava/util/List;
            move-result-object v${site.images}
        """.trimIndent())
        mutable(settingClass, settingMethod).addInstructions(0, """
            invoke-static {p1, p0}, $HELPER->addSettingsMenu(Landroid/view/Menu;Landroid/app/Activity;)V
        """.trimIndent())
        mutable(appClass, appMethod).addInstructions(0, """
            invoke-static/range {p0 .. p0}, $HELPER->initialize(Landroid/content/Context;)V
        """.trimIndent())
        println("BePTT URL filter: validated structural matches; injected image-list filter, settings menu and Application context. Existing preferences remain untouched.")
    }
}
