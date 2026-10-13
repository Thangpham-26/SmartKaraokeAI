package com.smartkaraoke.ai

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.view.WindowCompat
import androidx.lifecycle.viewmodel.compose.viewModel
import org.json.JSONObject

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = Paper.toArgb()
        window.navigationBarColor = Ink.toArgb()
        WindowCompat.getInsetsController(window, window.decorView).isAppearanceLightStatusBars = true
        setContent { KaraokeTheme { AnalysisScreen() } }
    }
}

@Composable
private fun SoundMark(modifier: Modifier = Modifier, color: Color = Mint) {
    Canvas(modifier) {
        val heights = listOf(0.25f, 0.55f, 0.88f, 0.42f, 0.7f)
        val width = size.width / 9f
        heights.forEachIndexed { i, fraction ->
            val h = size.height * fraction
            drawRoundRect(color, Offset(i * width * 1.8f, (size.height - h) / 2), Size(width, h), CornerRadius(width / 2))
        }
    }
}

@Composable
private fun StepCard(number: String, title: String, subtitle: String, content: @Composable ColumnScope.() -> Unit) {
    Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = Color.White)) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(42.dp).background(SoftTeal, RoundedCornerShape(12.dp)), contentAlignment = Alignment.Center) {
                    Text(number, color = Teal, style = MaterialTheme.typography.titleLarge)
                }
                Text(title, Modifier.weight(1f), style = MaterialTheme.typography.titleLarge)
            }
            Text(subtitle, color = Muted, style = MaterialTheme.typography.bodyLarge)
            content()
        }
    }
}

@Composable
private fun MainButton(text: String, enabled: Boolean = true, onClick: () -> Unit) {
    Button(onClick, enabled = enabled, modifier = Modifier.fillMaxWidth().heightIn(min = 60.dp),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 16.dp), shape = RoundedCornerShape(16.dp)) {
        Text(text, style = MaterialTheme.typography.labelLarge)
    }
}

@Composable
fun AnalysisScreen(vm: AnalysisViewModel = viewModel()) {
    val context = LocalContext.current
    val focus = LocalFocusManager.current
    val prefs = remember { context.getSharedPreferences("profiles", 0) }
    var baseUrl by rememberSaveable { mutableStateOf(prefs.getString("backend_url", "http://127.0.0.1:8000") ?: "http://127.0.0.1:8000") }
    var room by rememberSaveable { mutableStateOf("") }
    var vocal by rememberSaveable { mutableStateOf("") }
    var vocalMenu by remember { mutableStateOf(false) }
    var settingsOpen by rememberSaveable { mutableStateOf(false) }
    var roomOpen by rememberSaveable { mutableStateOf(false) }
    var selectedUriText by rememberSaveable { mutableStateOf<String?>(null) }
    var tab by rememberSaveable { mutableStateOf(0) }
    var device by rememberSaveable { mutableStateOf("JBL K12 Plus") }
    var notes by rememberSaveable { mutableStateOf("") }
    var rating by rememberSaveable { mutableStateOf(0) }
    var saved by remember { mutableStateOf(prefs.getString("last_profile", null)) }
    var saveMessage by remember { mutableStateOf("") }
    val scroll = rememberScrollState()
    val current = vm.result
    val voiceOptions = linkedMapOf("" to "Chưa rõ · Có thể bỏ qua", "male_thick" to "Nam · Giọng dày",
        "male_normal" to "Nam · Giọng thường", "male_weak" to "Nam · Giọng nhẹ",
        "female_high" to "Nữ · Giọng cao", "female_normal" to "Nữ · Giọng thường", "female_weak" to "Nữ · Giọng nhẹ")
    LaunchedEffect(Unit) { vm.checkConnection(baseUrl) }
    LaunchedEffect(current?.optString("analysis_id")) {
        if (current != null) {
            tab = 1; rating = 0; saveMessage = ""
        }
    }
    LaunchedEffect(tab) { scroll.scrollTo(0) }
    LaunchedEffect(vm.message) {
        if (vm.isError || vm.busy) scroll.animateScrollTo(0)
    }
    BackHandler(tab != 0) { tab = 0 }
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) {
            runCatching { context.contentResolver.takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION) }
            selectedUriText = uri.toString(); tab = 0
            vm.fileSelected(context, uri)
        }
    }
    Scaffold(containerColor = Paper, bottomBar = {
        NavigationBar(containerColor = Color.White, tonalElevation = 0.dp) {
            listOf("Bản thu", "Cách chỉnh", "Đã lưu").forEachIndexed { index, label ->
                NavigationBarItem(selected = tab == index, onClick = { focus.clearFocus(); tab = index },
                    icon = { Text((index + 1).toString(), fontWeight = FontWeight.Bold, fontSize = 22.sp) },
                    label = { Text(label, style = MaterialTheme.typography.labelMedium) },
                    colors = NavigationBarItemDefaults.colors(indicatorColor = SoftTeal, selectedIconColor = Teal,
                        selectedTextColor = Teal, unselectedIconColor = Muted, unselectedTextColor = Muted))
            }
        }
    }) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).imePadding().verticalScroll(scroll).padding(horizontal = 16.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(18.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Box(Modifier.size(46.dp).background(Teal, RoundedCornerShape(14.dp)).padding(10.dp)) { SoundMark(Modifier.fillMaxSize()) }
                Column {
                    Text("SmartKaraokeAI", style = MaterialTheme.typography.titleLarge)
                    Text("Hát thoải mái. Chỉnh thật dễ.", color = Muted, style = MaterialTheme.typography.bodyMedium)
                }
            }
            if (vm.message.isNotBlank() && (vm.busy || vm.isError || tab == 0)) {
                Card(colors = CardDefaults.cardColors(containerColor = if (vm.isError) MaterialTheme.colorScheme.errorContainer else SoftTeal)) {
                    Column(Modifier.fillMaxWidth().padding(16.dp).semantics { liveRegion = LiveRegionMode.Polite },
                        verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        Text(vm.message, color = if (vm.isError) MaterialTheme.colorScheme.onErrorContainer else Ink,
                            style = MaterialTheme.typography.bodyLarge)
                        if (vm.busy) LinearProgressIndicator(Modifier.fillMaxWidth(), color = Teal)
                    }
                }
            }
            when (tab) {
                0 -> {
                    Box(Modifier.fillMaxWidth().background(Brush.linearGradient(listOf(Ink, Color(0xFF175E58))), RoundedCornerShape(24.dp)).padding(24.dp)) {
                        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            SoundMark(Modifier.width(70.dp).height(34.dp))
                            Text("Giọng hát của bạn,\nâm thanh vừa ý hơn.", color = Color.White, style = MaterialTheme.typography.headlineMedium)
                            Text("Chọn bản thu. Nhận gợi ý. Chỉnh theo hình.", color = Color(0xFFD4F2E7), style = MaterialTheme.typography.bodyLarge)
                        }
                    }
                    StepCard("1", "Chọn bản thu giọng hát", "Hát một đoạn không có nhạc nền, rồi chọn file để phân tích.") {
                        if (selectedUriText != null) {
                            Text("Đã chọn: ${vm.fileName.ifBlank { "Bản thu của bạn" }}", color = Teal, style = MaterialTheme.typography.titleMedium)
                        }
                        MainButton(if (selectedUriText == null) "Chọn file âm thanh" else "Chọn bản thu khác", !vm.busy) {
                            focus.clearFocus(); picker.launch(arrayOf("audio/*", "video/mp4", "application/mp4", "application/ogg"))
                        }
                        Text("WAV, FLAC, OGG, MP4 hoặc M4A · 1–60 giây · Tối đa 20 MiB", color = Muted, style = MaterialTheme.typography.bodyMedium)
                    }
                    StepCard("2", "Nhận gợi ý chỉnh vang", "Bạn có thể chọn loại giọng, hoặc để trống nếu chưa rõ.") {
                        Box {
                            OutlinedButton(onClick = { vocalMenu = true }, enabled = !vm.busy,
                                modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp)) {
                                Text(voiceOptions[vocal] ?: "Chưa rõ loại giọng")
                            }
                            DropdownMenu(vocalMenu, onDismissRequest = { vocalMenu = false }) {
                                voiceOptions.forEach { (key, label) ->
                                    DropdownMenuItem(text = { Text(label, style = MaterialTheme.typography.bodyLarge) },
                                        onClick = { vocal = key; vocalMenu = false }, modifier = Modifier.heightIn(min = 56.dp))
                                }
                            }
                        }
                        MainButton(if (vm.busy) "Đang xử lý…" else "Phân tích giọng hát", selectedUriText != null && !vm.busy) {
                            focus.clearFocus()
                            selectedUriText?.let { vm.analyze(context, Uri.parse(it), baseUrl, room, vocal.ifBlank { null }) }
                        }
                        if (selectedUriText == null) Text("Hãy chọn bản thu ở bước 1 trước.", color = Muted)
                        TextButton(onClick = { roomOpen = !roomOpen }, modifier = Modifier.heightIn(min = 56.dp)) {
                            Text(if (roomOpen) "Ẩn thông tin phòng" else "Thông tin phòng · Không bắt buộc")
                        }
                        if (roomOpen) {
                            Text("Nếu đã đo thời gian vang RT60 của phòng, nhập số giây. Chưa đo thì để trống.", style = MaterialTheme.typography.bodyMedium)
                            OutlinedTextField(room, { room = it }, label = { Text("Thời gian vang RT60 (giây)") },
                                enabled = !vm.busy, singleLine = true, modifier = Modifier.fillMaxWidth())
                        }
                    }
                    Card(colors = CardDefaults.cardColors(containerColor = Color.White)) {
                        Column(Modifier.fillMaxWidth().padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                                Box(Modifier.size(12.dp).background(if (vm.connectionReady == true) Teal else Color(0xFFB47618), RoundedCornerShape(6.dp)))
                                Text(if (vm.connectionReady == true) "Máy tính đã kết nối" else "Kết nối với máy tính", style = MaterialTheme.typography.titleMedium)
                            }
                            OutlinedButton(onClick = { settingsOpen = !settingsOpen }, modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp)) {
                                Text(if (settingsOpen) "Ẩn thiết lập kết nối" else "Thiết lập kết nối")
                            }
                            if (settingsOpen) {
                                Text("USB: giữ cáp kết nối. Wi-Fi: dùng địa chỉ máy tính cùng mạng.", style = MaterialTheme.typography.bodyMedium, color = Muted)
                                OutlinedTextField(baseUrl, { baseUrl = it; prefs.edit().putString("backend_url", it).apply() },
                                    label = { Text("Địa chỉ máy tính") }, enabled = !vm.busy, singleLine = true, modifier = Modifier.fillMaxWidth())
                                OutlinedButton(onClick = { baseUrl = "http://127.0.0.1:8000"; prefs.edit().putString("backend_url", baseUrl).apply() },
                                    enabled = !vm.busy, modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp)) { Text("Dùng kết nối USB") }
                                MainButton("Kiểm tra kết nối", !vm.busy) { focus.clearFocus(); vm.checkConnection(baseUrl) }
                                Text("Máy ảo Android Studio dùng http://10.0.2.2:8000.", style = MaterialTheme.typography.bodyMedium, color = Muted)
                            }
                        }
                    }
                }
                1 -> {
                    if (current == null) {
                        EmptyCard("Chưa có hướng dẫn", "Phân tích bản thu trước. Sau đó, các núm chỉnh sẽ xuất hiện tại đây.") { tab = 0 }
                    } else {
                        Text("Chỉnh lần lượt 3 mục bên dưới.", color = Muted, style = MaterialTheme.typography.bodyLarge)
                        val recommendations = current.getJSONObject("recommendations")
                        var deviceMenu by remember { mutableStateOf(false) }
                        Box {
                            OutlinedButton(onClick = { deviceMenu = true }, modifier = Modifier.fillMaxWidth().heightIn(min = 60.dp)) { Text("Thiết bị: $device") }
                            DropdownMenu(deviceMenu, onDismissRequest = { deviceMenu = false }) {
                                recommendations.keys().forEach { name ->
                                    DropdownMenuItem(text = { Text(name, style = MaterialTheme.typography.bodyLarge) },
                                        onClick = { device = name; deviceMenu = false }, modifier = Modifier.heightIn(min = 56.dp))
                                }
                            }
                        }
                        val parameters = recommendations.optJSONObject(device)
                        if (parameters != null) {
                            DspCard(device, parameters)
                            MainButton("Lưu hướng dẫn này", !vm.busy) {
                                val profile = JSONObject().put("device", device).put("parameters", parameters)
                                    .put("analysis_id", current.getString("analysis_id"))
                                saved = profile.toString(); prefs.edit().putString("last_profile", saved).apply()
                                saveMessage = "Đã lưu. Bạn có thể mở lại ở mục Đã lưu."
                            }
                            if (saveMessage.isNotBlank()) Text(saveMessage, color = Teal, style = MaterialTheme.typography.bodyLarge)
                        }
                        FeedbackCard(rating, { rating = it }, notes, { if (it.length <= 2000) notes = it }, !vm.busy) {
                            focus.clearFocus(); vm.feedback(device, rating, notes)
                        }
                        if (vm.message == "Đã lưu đánh giá.") Text(vm.message, color = Teal)
                        var details by rememberSaveable { mutableStateOf(false) }
                        TextButton(onClick = { details = !details }, modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp)) {
                            Text(if (details) "Ẩn thông tin phân tích" else "Xem thông tin phân tích")
                        }
                        if (details) {
                            Card(colors = CardDefaults.cardColors(containerColor = Color.White)) {
                                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                    Text(if (parameters?.optBoolean("trained_on_mock") == true) "Mô hình demo từ dữ liệu mô phỏng." else "Gợi ý thử nghiệm; chưa xác minh thông số thiết bị.")
                                    val features = current.getJSONObject("features")
                                    Text("Bản thu: ${DialScale.label(features.getDouble("duration_seconds"))} giây")
                                    Text("Mức âm thanh: ${DialScale.label(features.getDouble("rms_dbfs"))} dBFS")
                                    Text("Chỉ báo kỹ thuật", style = MaterialTheme.typography.titleMedium)
                                    val warnings = current.getJSONArray("warnings")
                                    for (i in 0 until warnings.length()) Text(warnings.getString(i), style = MaterialTheme.typography.bodyMedium)
                                }
                            }
                        }
                    }
                }
                2 -> {
                    Text("Hướng dẫn đã lưu", style = MaterialTheme.typography.headlineMedium)
                    val profile = saved?.let { runCatching { JSONObject(it) }.getOrNull() }
                    if (profile == null) {
                        EmptyCard("Chưa lưu cấu hình nào", "Sau khi phân tích, chọn Lưu hướng dẫn này để xem lại khi cần.") { tab = 0 }
                    } else {
                        Text(profile.getString("device"), color = Teal, style = MaterialTheme.typography.titleLarge)
                        Text("Đây là cấu hình bạn đã lưu gần nhất.", color = Muted, style = MaterialTheme.typography.bodyLarge)
                        DspCard(profile.getString("device"), profile.getJSONObject("parameters"))
                    }
                }
            }
            Spacer(Modifier.height(8.dp))
        }
    }
}

@Composable
private fun EmptyCard(title: String, detail: String, onClick: () -> Unit) {
    Card(colors = CardDefaults.cardColors(containerColor = Color.White)) {
        Column(Modifier.padding(24.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Text(title, style = MaterialTheme.typography.titleLarge)
            Text(detail, style = MaterialTheme.typography.bodyLarge, color = Muted)
            MainButton("Chọn bản thu", onClick = onClick)
        }
    }
}

@Composable
private fun FeedbackCard(rating: Int, onRating: (Int) -> Unit, notes: String, onNotes: (String) -> Unit,
                         enabled: Boolean, onSubmit: () -> Unit) {
    Card(colors = CardDefaults.cardColors(containerColor = Color.White)) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Âm thanh đã vừa ý chưa?", style = MaterialTheme.typography.titleLarge)
            Text("1: Chưa vừa ý · 5: Rất hài lòng", color = Muted, style = MaterialTheme.typography.bodyMedium)
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                (1..5).forEach { value ->
                    OutlinedButton(onClick = { onRating(value) }, enabled = enabled,
                        modifier = Modifier.weight(1f).heightIn(min = 56.dp), contentPadding = PaddingValues(0.dp),
                        colors = ButtonDefaults.outlinedButtonColors(containerColor = if (rating == value) SoftTeal else Color.Transparent)) {
                        Text(value.toString(), fontSize = 22.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }
            OutlinedTextField(notes, onNotes, label = { Text("Nhận xét thêm · Có thể bỏ qua") }, enabled = enabled, modifier = Modifier.fillMaxWidth())
            MainButton("Gửi đánh giá", enabled && rating > 0, onSubmit)
        }
    }
}
