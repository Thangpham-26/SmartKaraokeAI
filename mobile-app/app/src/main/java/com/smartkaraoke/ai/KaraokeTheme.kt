package com.smartkaraoke.ai

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

val Ink = Color(0xFF152E36)
val Teal = Color(0xFF006B59)
val Mint = Color(0xFF73E6BF)
val Paper = Color(0xFFF5F6F1)
val SoftTeal = Color(0xFFE1F3EB)
val Muted = Color(0xFF4C6267)

@Composable
fun KaraokeTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = lightColorScheme(
            primary = Teal, onPrimary = Color.White,
            primaryContainer = SoftTeal, onPrimaryContainer = Ink,
            secondary = Ink, onSecondary = Color.White,
            background = Paper, onBackground = Ink,
            surface = Color.White, onSurface = Ink,
            surfaceVariant = SoftTeal, onSurfaceVariant = Muted,
            outline = Color(0xFF718582),
            error = Color(0xFFAB2929), errorContainer = Color(0xFFFFE9E6),
            onErrorContainer = Color(0xFF742020),
        ),
        typography = Typography(
            headlineLarge = TextStyle(fontFamily = FontFamily.SansSerif, fontWeight = FontWeight.Bold, fontSize = 32.sp, lineHeight = 39.sp),
            headlineMedium = TextStyle(fontWeight = FontWeight.Bold, fontSize = 27.sp, lineHeight = 34.sp),
            titleLarge = TextStyle(fontWeight = FontWeight.Bold, fontSize = 23.sp, lineHeight = 30.sp),
            titleMedium = TextStyle(fontWeight = FontWeight.SemiBold, fontSize = 20.sp, lineHeight = 27.sp),
            bodyLarge = TextStyle(fontSize = 19.sp, lineHeight = 28.sp),
            bodyMedium = TextStyle(fontSize = 17.sp, lineHeight = 25.sp),
            labelLarge = TextStyle(fontWeight = FontWeight.SemiBold, fontSize = 18.sp, lineHeight = 25.sp),
            labelMedium = TextStyle(fontWeight = FontWeight.Medium, fontSize = 16.sp, lineHeight = 22.sp),
        ),
        shapes = Shapes(small = RoundedCornerShape(12.dp), medium = RoundedCornerShape(20.dp), large = RoundedCornerShape(24.dp)),
        content = content,
    )
}
