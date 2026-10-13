package com.smartkaraoke.ai

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.text.font.FontWeight
import kotlin.math.cos
import kotlin.math.sin
import org.json.JSONObject

@Composable
fun PercentKnob(value: Double, label: String, modifier: Modifier = Modifier) {
    val percent = DialScale.percent(value)
    Column(modifier.width(108.dp).clearAndSetSemantics {
        contentDescription = "Núm minh họa $label, ${DialScale.label(value)} phần trăm, thang 0 đến 100"
    }, horizontalAlignment = Alignment.CenterHorizontally) {
        Canvas(Modifier.size(104.dp)) {
            val c = center
            val r = size.minDimension * 0.39f
            fun point(angle: Float, radius: Float): Offset {
                val radians = Math.toRadians(angle.toDouble())
                return Offset(c.x + cos(radians).toFloat() * radius, c.y + sin(radians).toFloat() * radius)
            }
            drawCircle(Color.Black.copy(alpha = 0.25f), r * 0.83f, c + Offset(0f, 5.dp.toPx()))
            for (i in 0..20) {
                val angle = 135f + i * 13.5f
                drawLine(if (i <= percent / 5f) Mint else Color(0xFF67818A), point(angle, r * 1.08f),
                    point(angle, r * (if (i % 5 == 0) 1.24f else 1.17f)), 1.5.dp.toPx(), StrokeCap.Round)
            }
            val origin = Offset(c.x - r, c.y - r)
            drawArc(Color(0xFF3E5962), 135f, 270f, false, origin, Size(2 * r, 2 * r), style = Stroke(3.dp.toPx(), cap = StrokeCap.Round))
            if (percent > 0) drawArc(Mint, 135f, percent * 2.7f, false, origin, Size(2 * r, 2 * r),
                style = Stroke(3.dp.toPx(), cap = StrokeCap.Round))
            drawCircle(Brush.linearGradient(listOf(Color(0xFF779098), Color(0xFF1A3039))), r * 0.81f)
            drawCircle(Brush.radialGradient(listOf(Color(0xFF405D68), Color(0xFF14282F))), r * 0.71f)
            drawCircle(Color.White.copy(alpha = 0.1f), r * 0.71f, style = Stroke(1.dp.toPx()))
            val angle = DialScale.angle(value)
            drawLine(Mint, point(angle, r * 0.30f), point(angle, r * 0.66f), 4.dp.toPx(), StrokeCap.Round)
            drawCircle(Mint, 2.dp.toPx(), point(angle, r * 0.66f))
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text("0%", color = Color(0xFFB9CED3), fontSize = 14.sp)
            Text("100%", color = Color(0xFFB9CED3), fontSize = 14.sp)
        }
    }
}

@Composable
private fun KnobRow(name: String, hardwareLabel: String, value: Double, hint: String) {
    Row(Modifier.fillMaxWidth().padding(vertical = 10.dp), verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(14.dp)) {
        PercentKnob(value, hardwareLabel)
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(name, color = Color.White, style = MaterialTheme.typography.titleMedium)
            Text(hardwareLabel, color = Color(0xFFB9CED3), style = MaterialTheme.typography.labelMedium)
            Text("${DialScale.label(value)}%", color = Mint, fontSize = 34.sp, fontWeight = FontWeight.Bold)
            Text(hint, color = Color(0xFFDFEAED), style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Composable
private fun NumericSetting(name: String, value: String, explanation: String) {
    Column(Modifier.fillMaxWidth().background(Color(0xFF233F49), RoundedCornerShape(14.dp)).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(5.dp)) {
        Text(name, color = Color(0xFFDFEAED), style = MaterialTheme.typography.labelLarge)
        Text(value, color = Mint, fontSize = 30.sp, fontWeight = FontWeight.Bold)
        Text(explanation, color = Color(0xFFDFEAED), style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun GuideGroup(step: String, title: String, caption: String, resetKey: String, content: @Composable ColumnScope.() -> Unit) {
    var done by rememberSaveable(resetKey) { mutableStateOf(false) }
    Card(colors = CardDefaults.cardColors(containerColor = Ink), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Box(Modifier.size(40.dp).background(Mint, RoundedCornerShape(12.dp)), contentAlignment = Alignment.Center) {
                    Text(step, color = Ink, fontWeight = FontWeight.Bold, fontSize = 22.sp)
                }
                Text(title, color = Color.White, style = MaterialTheme.typography.titleLarge, modifier = Modifier.weight(1f))
            }
            Text(caption, color = Color(0xFFB9CED3), style = MaterialTheme.typography.bodyMedium)
            content()
            Row(Modifier.fillMaxWidth().heightIn(min = 56.dp)
                .background(if (done) Color(0xFF204F43) else Color(0xFF233F49), RoundedCornerShape(12.dp))
                .toggleable(done, role = Role.Checkbox, onValueChange = { done = it }).padding(horizontal = 12.dp),
                verticalAlignment = Alignment.CenterVertically) {
                Checkbox(done, onCheckedChange = null, colors = CheckboxDefaults.colors(checkedColor = Mint,
                    uncheckedColor = Color(0xFFB9CED3), checkmarkColor = Ink))
                Text(if (done) "Đã chỉnh xong mục này" else "Đánh dấu khi đã chỉnh xong", color = Color.White,
                    style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(start = 10.dp))
            }
        }
    }
}

@Composable
fun DspCard(device: String, parameters: JSONObject) {
    val echo = parameters.optJSONObject("echo") ?: return
    val reverb = parameters.optJSONObject("reverb") ?: return
    val reset = device + parameters.toString()
    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Card(colors = CardDefaults.cardColors(containerColor = Color(0xFFFFF0D5))) {
            Text("Núm mô phỏng 0–100%, chưa hiệu chuẩn vị trí kim. Đối chiếu số trên thiết bị.",
                Modifier.padding(16.dp), color = Color(0xFF624508), style = MaterialTheme.typography.bodyMedium)
        }
        GuideGroup("1", "Giọng micro", "Tìm mục MIC EQ trên thiết bị.", reset) {
            if (parameters.has("mic_eq")) {
                val eq = parameters.getJSONObject("mic_eq")
                KnobRow("Âm trầm", "BASS", eq.getDouble("bass_pct"), "Chỉnh Bass về mức này.")
                KnobRow("Âm trung", "MID", eq.getDouble("mid_pct"), "Chỉnh Mid về mức này.")
                KnobRow("Âm cao", "TREBLE", eq.getDouble("treble_pct"), "Chỉnh Treble về mức này.")
            } else {
                val eq = parameters.optJSONObject("eq")
                if (eq != null) {
                    NumericSetting("Âm trầm · LOW", "${DialScale.label(eq.getDouble("low_gain_db"))} dB", "Nhập giá trị EQ; chưa có quy đổi vị trí núm.")
                    NumericSetting("Âm trung · MID", "${DialScale.label(eq.getDouble("mid_gain_db"))} dB", "Nhập đúng giá trị trên màn hình thiết bị.")
                    NumericSetting("Âm cao · HIGH", "${DialScale.label(eq.getDouble("high_gain_db"))} dB", "Nhập đúng giá trị trên màn hình thiết bị.")
                }
            }
        }
        GuideGroup("2", "Tiếng lặp", "Tìm mục ECHO trên thiết bị.", reset) {
            if (echo.has("level_pct")) {
                KnobRow("Mức tiếng lặp", "ECHO LEVEL", echo.getDouble("level_pct"), "Độ lớn của tiếng lặp.")
                KnobRow("Độ lặp lại", "REPEAT", echo.getDouble("repeat_pct"), "Mức lặp kéo dài của tiếng hát.")
            } else {
                KnobRow("Mức tiếng lặp", "ECHO MIX", echo.getDouble("mix_percent"), "Tỷ lệ tiếng lặp trong âm thanh.")
                KnobRow("Độ lặp lại", "FEEDBACK", echo.getDouble("feedback_percent"), "Mức phản hồi của tiếng lặp.")
            }
            NumericSetting("Thời gian lặp · DELAY", "${echo.getInt("delay_ms")} ms", "Nhập giá trị thời gian; không quy đổi sang phần trăm núm.")
        }
        GuideGroup("3", "Độ vang", "Tìm mục REVERB trên thiết bị.", reset) {
            if (reverb.has("level_pct")) {
                KnobRow("Mức độ vang", "REVERB LEVEL", reverb.getDouble("level_pct"), "Độ lớn của hiệu ứng vang.")
                NumericSetting("Kiểu vang · MODE", reverb.getInt("mode").toString(), "Chọn chế độ này trên thiết bị.")
            } else {
                KnobRow("Mức độ vang", "REVERB MIX", reverb.getDouble("mix_percent"), "Tỷ lệ tiếng vang trong âm thanh.")
                NumericSetting("Đuôi vang · DECAY", "${DialScale.label(reverb.getDouble("decay_seconds"))} giây", "Nhập thời gian đuôi vang trên màn hình thiết bị.")
            }
        }
    }
}
